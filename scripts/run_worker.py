"""Run one or more research jobs from the durable SQLite queue.

Usage:
    python scripts/run_worker.py             # keep polling
    python scripts/run_worker.py --once      # process at most one job
    python scripts/run_worker.py --max-jobs 2
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from spectrascholar.job_queue import claim_next, mark_done, recover_stale  # noqa: E402
from spectrascholar.research import run_research_job  # noqa: E402
from spectrascholar.schemas import ResearchRequest  # noqa: E402
from spectrascholar.settings import settings  # noqa: E402
from spectrascholar.store import (  # noqa: E402
    finish_job,
    get_job,
    init_store,
    is_cancel_requested,
)


def _run_one(item: dict) -> str:
    job_id = item["job_id"]
    trace_id = item["trace_id"]
    request = ResearchRequest.model_validate_json(item["request_json"])
    if is_cancel_requested(job_id):
        finish_job(job_id, "cancelled", error="用户取消", error_type="cancelled")
        mark_done(job_id, "cancelled", "用户取消")
        return "cancelled"
    try:
        asyncio.run(run_research_job(job_id, request, trace_id))
        job = get_job(job_id)
        status = job["status"] if job else "failed"
        mark_done(job_id, status, job.get("error") if job else "job missing")
        return status
    except Exception as exc:
        message = f"worker exception: {type(exc).__name__}: {exc}"
        if is_cancel_requested(job_id):
            finish_job(job_id, "cancelled", error="用户取消", error_type="cancelled")
            mark_done(job_id, "cancelled", "用户取消")
            return "cancelled"
        finish_job(job_id, "failed", error=message, error_type="worker_exception")
        mark_done(job_id, "failed", message)
        return "failed"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--max-jobs", type=int, default=0)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args()

    init_store()
    recovered = recover_stale()
    if recovered:
        print(f"recovered {recovered} stale queue row(s)")
    worker_id = args.worker_id or f"worker-{time.time_ns()}"
    processed = 0
    while True:
        item = claim_next(worker_id)
        if item is None:
            if args.once:
                print("queue empty")
                return 0
            time.sleep(settings.queue_poll_seconds)
            continue
        print(f"claimed {item['job_id']} (attempt {item['attempt']})")
        status = _run_one(item)
        processed += 1
        print(f"finished {item['job_id']}: {status}")
        if args.once or (args.max_jobs and processed >= args.max_jobs):
            return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
