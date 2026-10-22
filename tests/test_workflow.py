from __future__ import annotations

import asyncio
import time

from spectrascholar.schemas import WorkflowRequest
from spectrascholar.tools import ArxivSearchError
from spectrascholar.workflow import WorkflowState, _step_plan
from tests.conftest import upload_pdf


def _wait_workflow(client, workflow_id: str, tries: int = 200) -> dict:
    workflow = {}
    for _ in range(tries):
        workflow = client.get(f"/api/v1/workflows/{workflow_id}").json()
        if workflow.get("status") in {"completed", "failed", "cancelled"}:
            return workflow
        time.sleep(0.02)
    return workflow


def test_plan_invokes_arxiv_tool_and_keeps_results_outside_local_evidence(monkeypatch):
    import spectrascholar.workflow as workflow_module

    state = WorkflowState(
        req=WorkflowRequest(
            topic="hyperspectral graph neural network",
            document_ids=["a", "b"],
            tools=["arxiv_search"],
        )
    )

    def fake_load(document_id):
        return {"document_id": document_id, "filename": f"{document_id}.pdf"}, ["page text"]

    def fake_search(**kwargs):
        return {
            "returned": 1,
            "duplicates_filtered": 0,
            "attempts": 1,
            "papers": [
                {
                    "title": "External paper",
                    "entry_url": "https://arxiv.org/abs/2401.00001",
                    "year": 2024,
                    "doi": "10.1/x",
                }
            ],
        }

    monkeypatch.setattr(workflow_module, "_load_document", fake_load)
    monkeypatch.setattr(workflow_module, "search_arxiv", fake_search)
    summary = asyncio.run(_step_plan(state))
    assert "arXiv 工具调用完成" in summary
    assert state.tool_calls[0]["status"] == "completed"
    assert state.tool_calls[0]["returned"] == 1
    assert state.arxiv_results[0]["title"] == "External paper"
    assert state.notes and "不进入本地证据链" in state.notes[0]


def test_plan_arxiv_tool_failure_does_not_fail_local_workflow(monkeypatch):
    import spectrascholar.workflow as workflow_module

    state = WorkflowState(
        req=WorkflowRequest(
            topic="hyperspectral graph neural network",
            document_ids=["a", "b"],
            tools=["arxiv_search"],
        )
    )

    def fake_load(document_id):
        return {"document_id": document_id, "filename": f"{document_id}.pdf"}, ["page text"]

    def fake_search(**kwargs):
        raise ArxivSearchError("arxiv_unavailable", "network down")

    monkeypatch.setattr(workflow_module, "_load_document", fake_load)
    monkeypatch.setattr(workflow_module, "search_arxiv", fake_search)
    summary = asyncio.run(_step_plan(state))
    assert "arXiv 工具失败" in summary
    assert state.tool_calls[0]["status"] == "failed"
    assert state.arxiv_results == []
    assert state.notes


def test_workflow_completes_all_steps_and_exports_report(client, two_papers):
    first, second = two_papers
    response = client.post(
        "/api/v1/workflows",
        json={
            "topic": "比较动态图 GNN 与 HybridSN 在 Indian Pines 上的实验设置",
            "document_ids": [first["document_id"], second["document_id"]],
            "extraction_mode": "heuristic",
            "idempotency_key": "demo-workflow-1",
        },
    )
    assert response.status_code == 202, response.text
    workflow_id = response.json()["workflow_id"]
    workflow = _wait_workflow(client, workflow_id)
    assert workflow["status"] == "completed", workflow
    assert workflow["comparison_id"]
    assert workflow["report"]
    assert "引用核验报告（自动生成）" in workflow["report"]
    assert "工作流边界" in workflow["report"]
    assert workflow["citation_audit"]["verified_local"] >= 1

    steps = workflow["steps"]
    assert [step["name"] for step in steps] == [
        "plan",
        "screen",
        "retrieve",
        "extract",
        "verify",
        "compare",
        "report",
    ]
    assert all(step["status"] == "completed" for step in steps)
    assert all(step["finished_at"] for step in steps)

    download = client.get(f"/api/v1/workflows/{workflow_id}.md")
    assert download.status_code == 200
    assert "科研文献调研报告" in download.text

    # Same idempotency key must not create a second run.
    again = client.post(
        "/api/v1/workflows",
        json={
            "topic": "另一个主题也应该被幂等键拦截",
            "document_ids": [first["document_id"], second["document_id"]],
            "idempotency_key": "demo-workflow-1",
        },
    )
    assert again.status_code == 202
    assert again.json()["workflow_id"] == workflow_id


def test_workflow_fails_when_fewer_than_two_pdfs_have_text(client, two_papers):
    first, _ = two_papers
    blank = upload_pdf(client, "blank.pdf", [[""]])
    response = client.post(
        "/api/v1/workflows",
        json={
            "topic": "扫描件失败路径测试",
            "document_ids": [first["document_id"], blank["document_id"]],
            "extraction_mode": "heuristic",
        },
    )
    workflow = _wait_workflow(client, response.json()["workflow_id"])
    assert workflow["status"] == "failed"
    assert "至少需要 2 篇" in workflow["error"]
    screen = next(step for step in workflow["steps"] if step["name"] == "screen")
    assert screen["status"] == "failed"
    assert "扫描" in screen["error"] or "至少需要" in screen["error"]


def test_workflow_validation(client, two_papers):
    first, _ = two_papers
    missing = client.post(
        "/api/v1/workflows",
        json={"topic": "不存在的文献测试", "document_ids": [first["document_id"], "nope"]},
    )
    assert missing.status_code == 404
    duplicate = client.post(
        "/api/v1/workflows",
        json={"topic": "重复文献测试", "document_ids": [first["document_id"], first["document_id"]]},
    )
    assert duplicate.status_code == 422
    assert client.get("/api/v1/workflows/nope").status_code == 404
