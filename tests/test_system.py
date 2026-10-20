from __future__ import annotations

from dataclasses import replace

import spectrascholar.main as main_module
from spectrascholar.api import dependencies as dependencies_module
from spectrascholar.settings import settings


def test_health_and_trace_headers(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert response.headers["X-Trace-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"

    custom = client.get("/api/v1/health", headers={"X-Trace-ID": "my-trace_123"})
    assert custom.headers["X-Trace-ID"] == "my-trace_123"

    unsafe = client.get("/api/v1/health", headers={"X-Trace-ID": "bad trace with spaces"})
    assert unsafe.headers["X-Trace-ID"] != "bad trace with spaces"


def test_unknown_endpoint_returns_structured_error_with_trace(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "http_404"
    assert body["trace_id"]


def test_api_key_protection_when_configured(client, monkeypatch):
    protected = replace(settings, api_key="top-secret")
    monkeypatch.setattr(dependencies_module, "settings", protected)
    assert client.get("/api/v1/documents").status_code == 401
    rejected = client.get("/api/v1/documents", headers={"X-API-Key": "wrong"})
    assert rejected.status_code == 401
    accepted = client.get("/api/v1/documents", headers={"X-API-Key": "top-secret"})
    assert accepted.status_code == 200
    # Health stays public for container health checks.
    assert client.get("/api/v1/health").status_code == 200


def test_rate_limit_returns_429(client, monkeypatch):
    limited = replace(settings, rate_limit_per_minute=2, research_backend="demo")
    monkeypatch.setattr(main_module, "settings", limited)
    main_module._RATE_LIMIT.clear()
    payload = {"topic": "限流测试主题"}
    first = client.post("/api/v1/research", json=payload)
    second = client.post("/api/v1/research", json=payload)
    third = client.post("/api/v1/research", json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    assert third.json()["error_code"] == "rate_limited"


def test_config_endpoint_never_returns_secrets(client, monkeypatch):
    response = client.get("/api/v1/config")
    assert response.status_code == 200
    body = response.json()
    assert "api_key" not in body
    assert "OPENAI_API_KEY" not in response.text
    assert body["app"]["name"] == "SpectraScholar"
