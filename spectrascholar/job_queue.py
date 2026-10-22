"""SQLite-backed durable research job queue.

The API enqueues a job and returns 202; ``scripts/run_worker.py`` claims jobs
with ``BEGIN IMMEDIATE``, runs them, and marks them done. A worker crash leaves
a ``running`` row that another worker can recover after the lock timeout.

This is intentionally a small local queue, not a replacement for Redis/RQ at
multi-machine scale; it removes the V1 ``BackgroundTasks`` loss window.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from .schemas import ResearchRequest
from .settings import settings
from .store import connect, now_iso


def enqueue_job(job_id: str, trace_id: str, request: ResearchRequest) -> None:
    with connect() as connection:
        connection.execute(
            """INSERT INTO job_queue
               (job_id, trace_id, request_json, status, attempts, available_at,
                created_at, updated_at)
               VALUES (?, ?, ?, 'queued', 0, ?, ?, ?)""",
            (
                job_id,
                trace_id,
                request.model_dump_json(),
                now_iso(),
                now_iso(),
                now_iso(),
            ),
        )


def recover_stale() -> int:
    cutoff = (
        datetime.now(UTC) - timedelta(seconds=settings.queue_lock_timeout_seconds)
    ).isoformat(timespec="seconds")
    with connect() as connection:
        cursor = connection.execute(
            """UPDATE job_queue
               SET status='queued', locked_at=NULL, worker_id=NULL, updated_at=?
               WHERE status='running' AND locked_at IS NOT NULL AND locked_at < ?""",
            (now_iso(), cutoff),
        )
        return int(cursor.rowcount or 0)


def claim_next(worker_id: str | None = None) -> dict | None:
    """Atomically claim one queued job; returns None when the queue is empty."""
    worker_id = worker_id or f"worker-{uuid4().hex[:8]}"
    now = now_iso()
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        cutoff = (
            datetime.now(UTC) - timedelta(seconds=settings.queue_lock_timeout_seconds)
        ).isoformat(timespec="seconds")
        connection.execute(
            """UPDATE job_queue
               SET status='queued', locked_at=NULL, worker_id=NULL, updated_at=?
               WHERE status='running' AND locked_at IS NOT NULL AND locked_at < ?""",
            (now, cutoff),
        )
        row = connection.execute(
            """SELECT job_id, trace_id, request_json, attempts
               FROM job_queue
               WHERE status='queued' AND available_at <= ?
               ORDER BY created_at, job_id
               LIMIT 1""",
            (now,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """UPDATE job_queue
               SET status='running', attempts=attempts+1, locked_at=?,
                   worker_id=?, updated_at=?
               WHERE job_id=? AND status='queued'""",
            (now, worker_id, now, row["job_id"]),
        )
        return {
            "job_id": row["job_id"],
            "trace_id": row["trace_id"],
            "request_json": row["request_json"],
            "attempt": int(row["attempts"]) + 1,
            "worker_id": worker_id,
        }


def mark_done(job_id: str, status: str, error: str | None = None) -> None:
    with connect() as connection:
        connection.execute(
            """UPDATE job_queue
               SET status=?, locked_at=NULL, worker_id=NULL, last_error=?, updated_at=?
               WHERE job_id=? AND status!='cancelled'""",
            (status, error, now_iso(), job_id),
        )


def queue_stats() -> dict[str, int]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT status, COUNT(*) AS count FROM job_queue GROUP BY status"
        ).fetchall()
    return {row["status"]: int(row["count"]) for row in rows}
