"""Workflow submission, step inspection and report download."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from ..logging_utils import new_trace_id
from ..schemas import WorkflowDetails, WorkflowRequest, WorkflowSubmitted
from ..settings import settings
from ..store import (
    create_workflow,
    get_document,
    get_workflow,
    get_workflow_by_idempotency,
    recent_workflows,
)
from ..workflow import run_workflow_job
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"], dependencies=[Depends(require_api_key)])


def _submitted(workflow_id: str, status: str, trace_id: str) -> WorkflowSubmitted:
    return WorkflowSubmitted(workflow_id=workflow_id, status=status, trace_id=trace_id)


@router.post("", response_model=WorkflowSubmitted, status_code=202)
async def start_workflow(req: WorkflowRequest, tasks: BackgroundTasks):
    for document_id in req.document_ids:
        if get_document(document_id) is None:
            raise HTTPException(status_code=404, detail=f"找不到论文: {document_id}")
    if req.idempotency_key:
        existing = get_workflow_by_idempotency(req.idempotency_key)
        if existing is not None:
            return _submitted(existing["workflow_id"], existing["status"], existing.get("trace_id") or "")
    active = sum(1 for row in recent_workflows(limit=100) if row["status"] in {"queued", "running"})
    if active >= settings.max_concurrent_jobs:
        raise HTTPException(status_code=429, detail="当前工作流并发已满，请稍后再试")
    trace_id = new_trace_id()
    workflow_id = create_workflow(req, trace_id)
    tasks.add_task(run_workflow_job, workflow_id, req)
    return _submitted(workflow_id, "queued", trace_id)


@router.get("", response_model=list[dict])
def workflow_history(limit: int = 20):
    return recent_workflows(limit=min(max(limit, 1), 100))


@router.get("/{workflow_id}.md")
def download_workflow_report(workflow_id: str):
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="工作流不存在")
    if workflow["status"] != "completed" or not workflow.get("report"):
        raise HTTPException(status_code=404, detail="工作流尚未完成")
    return PlainTextResponse(
        workflow["report"],
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="workflow-{workflow_id}.md"'},
    )


@router.get("/{workflow_id}", response_model=WorkflowDetails)
def workflow_detail(workflow_id: str):
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="工作流不存在")
    return WorkflowDetails(**{key: workflow.get(key) for key in WorkflowDetails.model_fields})
