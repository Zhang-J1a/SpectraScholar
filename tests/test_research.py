from __future__ import annotations

import time
from dataclasses import replace

import spectrascholar.api.research as api_research
import spectrascholar.research as research_module
from spectrascholar.settings import settings
from tests.conftest import install_fake_gptr, upload_pdf


def _wait(client, job_id: str, tries: int = 100) -> dict:
    job = {}
    for _ in range(tries):
        job = client.get(f"/api/v1/research/{job_id}").json()
        if job.get("status") in {"completed", "failed", "cancelled"}:
            return job
        time.sleep(0.02)
    return job


def _enable_gptr(monkeypatch, **overrides):
    new_settings = replace(settings, research_backend="gptr", **overrides)
    monkeypatch.setattr(api_research, "settings", new_settings)
    monkeypatch.setattr(research_module, "settings", new_settings)
    return new_settings


def test_demo_research_completes_with_explicit_demo_marker(client):
    response = client.post(
        "/api/v1/research",
        json={"topic": "比较高光谱分类中的动态图方法", "domain": "hyperspectral"},
    )
    assert response.status_code == 202
    submitted = response.json()
    assert submitted["is_demo"] is True
    assert submitted["backend"] == "demo"
    assert submitted["trace_id"]

    job = _wait(client, submitted["job_id"])
    assert job["status"] == "completed"
    assert job["is_demo"] is True
    assert "演示模式" in job["report"]
    assert "不是调研结果" in job["report"]
    assert job["elapsed_ms"] is not None and job["elapsed_ms"] >= 0
    assert job["metadata"]["backend"] == "demo"
    assert job["metadata"]["report_path"].endswith(".md")

    events = client.get(f"/api/v1/research/{submitted['job_id']}/events").json()
    assert any(event["step"] == "completed" for event in events)
    assert all(event["job_id"] == submitted["job_id"] for event in events)

    download = client.get(f"/api/v1/research/{submitted['job_id']}.md")
    assert download.status_code == 200
    assert "演示模式" in download.text
    assert "引用核验报告" in download.text


def test_gptr_mocked_success_records_real_backend(client, monkeypatch):
    install_fake_gptr(
        monkeypatch,
        report="# 真实适配器测试报告\n\n这是 Mock 引擎返回的内容。",
        context="Mock context about GNN papers.",
    )
    _enable_gptr(monkeypatch)
    response = client.post(
        "/api/v1/research",
        json={"topic": "图神经网络高光谱分类综述", "source": "web", "domain": "hyperspectral"},
    )
    assert response.status_code == 202
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "completed", job
    assert job["backend"] == "gptr"
    assert job["is_demo"] is False
    assert "GPT Researcher" in job["report"]
    assert "Mock 引擎返回的内容" in job["report"]

    from tests.conftest import FakeGPTResearcher

    assert FakeGPTResearcher.instances
    call = FakeGPTResearcher.instances[-1]
    assert call.kwargs["report_source"] == "web"
    assert call.kwargs["report_type"] == "research_report"
    assert call.config_data["REPORT_SOURCE"] == "web"
    assert call.config_data["RETRIEVER"] == "tavily"
    assert call.config_data["LANGUAGE"] == "chinese"


def test_gptr_local_mode_writes_config_with_doc_path(client, monkeypatch):
    upload_pdf(client, "local.pdf", [["Local PDF text for DOC_PATH verification."]])
    install_fake_gptr(monkeypatch, report="# Local report\n\nlocal")
    _enable_gptr(monkeypatch)
    response = client.post(
        "/api/v1/research",
        json={"topic": "本地论文调研测试", "source": "local", "domain": "hyperspectral"},
    )
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "completed", job

    from tests.conftest import FakeGPTResearcher

    call = FakeGPTResearcher.instances[-1]
    assert call.config_data["REPORT_SOURCE"] == "local"
    assert call.config_data["DOC_PATH"].endswith("papers")
    assert call.kwargs["report_source"] == "local"


def test_deepseek_provider_is_supported(client, monkeypatch):
    install_fake_gptr(monkeypatch, report="# DeepSeek mock report\n\nok")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-test-key")
    _enable_gptr(
        monkeypatch,
        gptr_fast_llm="deepseek:deepseek-chat",
        gptr_smart_llm="deepseek:deepseek-chat",
        gptr_strategic_llm="deepseek:deepseek-chat",
    )
    response = client.post("/api/v1/research", json={"topic": "DeepSeek 适配器测试主题"})
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "completed", job

    from tests.conftest import FakeGPTResearcher

    call = FakeGPTResearcher.instances[-1]
    assert call.config_data["FAST_LLM"] == "deepseek:deepseek-chat"
    assert call.config_data["SMART_LLM"] == "deepseek:deepseek-chat"
    assert call.config_data["CONTEXT_FILTER"] == "keyword"


def test_gptr_empty_report_fails_without_fake_success(client, monkeypatch):
    install_fake_gptr(monkeypatch, report="   ", context="some context")
    _enable_gptr(monkeypatch)
    response = client.post("/api/v1/research", json={"topic": "空报告失败测试"})
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "failed"
    assert job["error_type"] == "empty_report"
    assert "空报告" in job["error"]


def test_gptr_missing_key_fails_with_clear_error(client, monkeypatch):
    install_fake_gptr(monkeypatch, report="# would not run")
    _enable_gptr(monkeypatch)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/api/v1/research", json={"topic": "缺少密钥的失败测试"})
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "failed"
    assert job["error_type"] == "missing_api_key"
    assert "OPENAI_API_KEY" in job["error"]


def test_gptr_timeout_is_retried_then_fails(client, monkeypatch):
    install_fake_gptr(monkeypatch, report="# late", context="late context", delay=0.5)
    _enable_gptr(
        monkeypatch,
        research_phase_timeout_seconds=0.05,
        research_timeout_seconds=0.2,
        research_max_attempts=2,
        retry_backoff_seconds=0.0,
    )
    response = client.post("/api/v1/research", json={"topic": "超时重试测试"})
    job = _wait(client, response.json()["job_id"])
    assert job["status"] == "failed"
    assert job["error_type"] == "timeout"
    assert job["attempts"] == 2
    events = client.get(f"/api/v1/research/{job['job_id']}/events").json()
    assert any(event["step"] == "retry" for event in events)


def test_failed_job_can_be_retried(client, monkeypatch):
    install_fake_gptr(monkeypatch, report="# recovered", fail_on="conduct")
    _enable_gptr(monkeypatch)
    first = client.post("/api/v1/research", json={"topic": "可重试的失败任务"}).json()
    failed = _wait(client, first["job_id"])
    assert failed["status"] == "failed"
    retried = client.post(f"/api/v1/research/{first['job_id']}/retry")
    assert retried.status_code == 202
    second_job = _wait(client, retried.json()["job_id"])
    assert second_job["status"] == "failed"  # fake still fails; this only tests the retry endpoint


def test_invalid_requests_are_rejected(client):
    assert client.post("/api/v1/research", json={"topic": "短"}).status_code == 422
    assert client.post(
        "/api/v1/research", json={"topic": "合法长度主题", "source": "ftp"}
    ).status_code == 422
    missing = client.get("/api/v1/research/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["trace_id"]
