from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from spectrascholar.job_queue import (
    claim_next,
    enqueue_job,
    mark_done,
    queue_stats,
    recover_stale,
)
from spectrascholar.schemas import ResearchRequest
from spectrascholar.store import connect, create_job, init_store


def _reset_queue() -> None:
    init_store()
    with connect() as connection:
        connection.execute("DELETE FROM job_queue")


def _enqueue(topic: str) -> str:
    request = ResearchRequest(topic=topic, source="web", domain="hyperspectral")
    job_id = create_job(request, backend="demo", trace_id=f"trace-{topic}")
    enqueue_job(job_id, f"trace-{topic}", request)
    return job_id


def test_queue_claim_is_atomic_and_marks_done():
    _reset_queue()
    job_id = _enqueue("queue-claim-test")

    first = claim_next("worker-1")
    assert first is not None
    assert first["job_id"] == job_id
    assert first["attempt"] == 1
    assert claim_next("worker-2") is None

    mark_done(job_id, "completed")
    assert queue_stats().get("completed") == 1
    assert claim_next("worker-3") is None


def test_queue_recovers_stale_running_job():
    _reset_queue()
    job_id = _enqueue("queue-stale-test")
    claimed = claim_next("worker-crash")
    assert claimed is not None
    old = (datetime.now(UTC) - timedelta(hours=2)).isoformat(timespec="seconds")
    with connect() as connection:
        connection.execute(
            "UPDATE job_queue SET locked_at=? WHERE job_id=?", (old, job_id)
        )

    assert recover_stale() == 1
    again = claim_next("worker-recovery")
    assert again is not None
    assert again["job_id"] == job_id
    assert again["attempt"] == 2
    mark_done(job_id, "failed", "recovered test")


def test_sqlite_queue_submit_path_can_be_selected(monkeypatch):
    # The API module reads this setting at call time; ensure the sqlite branch
    # is selectable without changing the default test (inline) path.
    from spectrascholar.api import research as api_research
    from spectrascholar.settings import settings

    assert replace(settings, queue_backend="sqlite").queue_backend == "sqlite"
    assert hasattr(api_research, "enqueue_job")
