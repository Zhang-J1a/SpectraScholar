"""Research job submission, status, events and report download."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from ..job_queue import enqueue_job
from ..logging_utils import new_trace_id
from ..research import run_research_job
from ..schemas import JobDetails, JobEvent, JobStatus, JobSubmitted, JobSummary, ResearchRequest
from ..settings import settings
from ..store import (
    create_job,
    get_job,
    job_count,
    list_documents,
    list_job_events,
    recent_jobs,
    request_job_cancel,
)
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/research", tags=["research"], dependencies=[Depends(require_api_key)])


def _details(row: dict) -> JobDetails:
    return JobDetails(**{key: row.get(key) for key in JobDetails.model_fields})


def _submit(req: ResearchRequest, tasks: BackgroundTasks) -> JobSubmitted:
    trace_id = new_trace_id()
    backend = settings.research_backend
    job_id = create_job(req, backend=backend, trace_id=trace_id)
    if settings.queue_backend == "sqlite":
        enqueue_job(job_id, trace_id, req)
    else:
        tasks.add_task(run_research_job, job_id, req, trace_id)
    return JobSubmitted(
        job_id=job_id,
        status="queued",
        trace_id=trace_id,
        backend=backend,
        is_demo=backend == "demo",
    )


@router.post("", response_model=JobSubmitted, status_code=202)
async def start_research(req: ResearchRequest, tasks: BackgroundTasks):
    if req.source == "local" and not list_documents():
        raise HTTPException(status_code=400, detail="请先上传论文 PDF，再选择本地文档调研")
    active = job_count("queued") + job_count("running")
    if active >= settings.max_concurrent_jobs:
        raise HTTPException(
            status_code=429,
            detail=f"当前已有 {active} 个研究任务在排队/运行，请稍后再试",
        )
    return _submit(req, tasks)


@router.get("", response_model=list[JobSummary])
def research_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: JobStatus | None = None,
):
    return [
        JobSummary(**{key: row.get(key) for key in JobSummary.model_fields})
        for row in recent_jobs(limit=limit, status=status, offset=offset)
    ]


@router.get("/{job_id}.md")
def download_report(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] != "completed" or not job.get("report"):
        raise HTTPException(status_code=404, detail="报告不存在或尚未完成")
    path = settings.report_dir / f"{job_id}.md"
    headers = {"Content-Disposition": f'attachment; filename="{job_id}.md"'}
    if path.is_file():
        return FileResponse(path, media_type="text/markdown; charset=utf-8", headers=headers)
    return PlainTextResponse(
        job["report"],
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )


@router.get("/{job_id}", response_model=JobDetails)
def research_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _details(job)


@router.get("/{job_id}/events", response_model=list[JobEvent])
def research_events(job_id: str, limit: int = Query(200, ge=1, le=1000)):
    if get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return [JobEvent(**row) for row in list_job_events(job_id, limit=limit)]


@router.post("/{job_id}/cancel", response_model=JobDetails)
def cancel_research(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="只有 queued/running 任务可以取消")
    updated = request_job_cancel(job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _details(updated)


@router.post("/{job_id}/retry", response_model=JobSubmitted, status_code=202)
async def retry_research(job_id: str, tasks: BackgroundTasks):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if job["status"] not in {"failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="只有失败或已取消的任务可以重试")
    req = ResearchRequest(
        topic=job["topic"],
        source=job["source"],
        domain=job["domain"],
        language=job.get("language") or "zh",
        max_elapsed_seconds=job.get("max_elapsed_seconds"),
        max_cost_usd=job.get("max_cost_usd"),
    )
    active = job_count("queued") + job_count("running")
    if active >= settings.max_concurrent_jobs:
        raise HTTPException(status_code=429, detail="并发任务已满，请稍后再试")
    return _submit(req, tasks)
