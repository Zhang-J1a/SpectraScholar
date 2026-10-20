"""Health, configuration and single-quote verification endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..evidence import PDFExtractionError, make_evidence_ref, read_pdf_pages
from ..rag.service import knowledge_status
from ..schemas import EvidenceRef, HealthResponse, VerifyEvidenceRequest
from ..settings import settings
from ..store import document_count, get_document
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health():
    try:
        kb = knowledge_status()
        chunks = int(kb.get("total_chunks", 0))
    except Exception:
        chunks = 0
    return HealthResponse(
        status="ok",
        app_version=settings.app_version,
        research_backend=settings.research_backend,
        extractor_backend=settings.extractor_backend,
        embedding_backend=settings.embedding_backend,
        answer_backend=settings.answer_backend,
        auth_enabled=bool(settings.api_key),
        demo_mode=settings.research_backend == "demo",
        knowledge_chunks=chunks,
        documents=document_count(),
    )


@router.get("/config", dependencies=[Depends(require_api_key)])
def config():
    return {"app": {"name": settings.app_name, "version": settings.app_version}, **settings.public_summary()}


@router.post(
    "/evidence/verify",
    response_model=EvidenceRef,
    dependencies=[Depends(require_api_key)],
)
def verify_evidence(req: VerifyEvidenceRequest):
    document = get_document(req.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    path = settings.paper_dir / document["stored_name"]
    try:
        pages = read_pdf_pages(path)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    reference = make_evidence_ref(
        req.document_id,
        pages,
        req.page,
        req.quote,
        value=req.value,
    )
    return reference
