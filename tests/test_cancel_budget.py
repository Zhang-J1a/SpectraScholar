from __future__ import annotations

from spectrascholar.job_queue import enqueue_job, mark_done, queue_stats
from spectrascholar.research import _effective_timeout, _extract_cost
from spectrascholar.schemas import ResearchRequest
from spectrascholar.settings import settings
from spectrascholar.store import (
    create_job,
    finish_job,
    get_job,
    mark_job_running,
    request_job_cancel,
)


def _request(**overrides) -> ResearchRequest:
    data = {"topic": "测试取消与预算的任务", "source": "web", "domain": "general"}
    data.update(overrides)
    return ResearchRequest(**data)


def test_cancel_queued_job_updates_jobs_and_queue():
    job_id = create_job(_request(), backend="demo", trace_id="trace-cancel")
    enqueue_job(job_id, "trace-cancel", _request())
    updated = request_job_cancel(job_id)
    assert updated is not None
    assert updated["status"] == "cancelled"
    assert queue_stats().get("cancelled") == 1

    # A late worker must not turn a cancelled queue row into completed.
    mark_done(job_id, "completed")
    assert queue_stats().get("cancelled") == 1
    assert queue_stats().get("completed", 0) == 0


def test_late_worker_completion_cannot_overwrite_cancelled_running_job():
    job_id = create_job(_request(), backend="demo", trace_id="trace-late")
    mark_job_running(job_id, 1)
    request_job_cancel(job_id)
    finish_job(job_id, "completed", report="late report")
    job = get_job(job_id)
    assert job["status"] == "cancelled"
    assert job["report"] is None


def test_cancel_running_job_sets_cooperative_flag():
    job_id = create_job(_request(), backend="demo", trace_id="trace-running")
    mark_job_running(job_id, 1)
    updated = request_job_cancel(job_id)
    assert updated is not None
    assert updated["status"] == "running"
    assert updated["cancel_requested"] is True
    assert get_job(job_id)["cancel_requested"] is True


def test_cancel_endpoint_cancels_queued_job(client):
    job_id = create_job(_request(), backend="demo", trace_id="trace-api-cancel")
    enqueue_job(job_id, "trace-api-cancel", _request())
    response = client.post(f"/api/v1/research/{job_id}/cancel")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancel_requested"] is True
    again = client.post(f"/api/v1/research/{job_id}/cancel")
    assert again.status_code == 409


def test_budget_helpers():
    request = _request(max_elapsed_seconds=120, max_cost_usd=0.5)
    assert _effective_timeout(request) == float(
        min(120, settings.research_timeout_seconds)
    )
    assert _extract_cost({"costs": {"total_cost": 0.42}}) == 0.42
    assert _extract_cost({"costs": "$0.125"}) == 0.125
    assert _extract_cost(None) is None
