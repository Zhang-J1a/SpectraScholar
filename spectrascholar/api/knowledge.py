"""Knowledge-base indexing, search and grounded Q&A endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..rag.service import (
    RAGError,
    answer_question,
    clear_knowledge,
    index_documents,
    knowledge_status,
    search_knowledge,
)
from ..schemas import (
    AnswerRequest,
    AnswerResponse,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
)
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/kb", tags=["knowledge-base"], dependencies=[Depends(require_api_key)])


def _raise_rag(exc: RAGError) -> None:
    status = 503 if exc.code == "missing_api_key" else 502
    if exc.code in {"invalid_embedding_backend"}:
        status = 400
    raise HTTPException(status_code=status, detail=f"{exc.code}: {exc}") from exc


@router.post("/index", response_model=IndexResponse)
async def index_knowledge(req: IndexRequest):
    try:
        return await index_documents(req.document_ids)
    except RAGError as exc:
        _raise_rag(exc)


@router.get("/status")
def status():
    return knowledge_status()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    try:
        return await search_knowledge(req)
    except RAGError as exc:
        _raise_rag(exc)


@router.post("/answer", response_model=AnswerResponse)
async def answer(req: AnswerRequest):
    try:
        return await answer_question(req)
    except RAGError as exc:
        _raise_rag(exc)


@router.delete("")
def clear():
    clear_knowledge()
    return {"cleared": True}
