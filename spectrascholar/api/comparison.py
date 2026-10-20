"""Multi-paper comparison endpoints and Markdown export."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from ..compare import build_comparison
from ..evidence import PDFExtractionError
from ..extraction import ExtractionError, extract_document, resolve_mode
from ..schemas import CompareRequest, ComparisonResponse
from ..settings import settings
from ..store import (
    get_comparison,
    get_document,
    list_comparisons,
    save_comparison,
)
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/compare", tags=["comparison"], dependencies=[Depends(require_api_key)])


def _raise_extraction(exc: Exception) -> None:
    if isinstance(exc, PDFExtractionError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if isinstance(exc, ExtractionError):
        if exc.code == "missing_api_key":
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        if exc.code in {"timeout", "provider_error"}:
            raise HTTPException(status_code=504, detail=str(exc)) from exc
        raise HTTPException(status_code=502, detail=f"抽取失败 ({exc.code}): {exc}") from exc
    raise HTTPException(status_code=500, detail=f"抽取失败: {type(exc).__name__}") from exc


@router.post("", response_model=ComparisonResponse)
async def compare_papers(req: CompareRequest):
    try:
        mode = resolve_mode(req.mode)
    except ExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    papers = []
    for document_id in req.document_ids:
        document = get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"找不到论文: {document_id}")
        path = settings.paper_dir / document["stored_name"]
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"论文文件已丢失: {document_id}")
        try:
            papers.append(
                await extract_document(
                    document_id,
                    document["filename"],
                    path,
                    mode,
                )
            )
        except (PDFExtractionError, ExtractionError) as exc:
            _raise_extraction(exc)
        except Exception as exc:
            _raise_extraction(exc)
    comparison = build_comparison(papers, extraction_mode=mode, language=req.language)
    saved_id = save_comparison(
        req.document_ids,
        mode,
        comparison.model_dump(mode="json"),
        comparison.markdown,
    )
    return comparison.model_copy(update={"comparison_id": saved_id})


@router.get("", response_model=list[dict])
def comparison_history(limit: int = 20):
    return list_comparisons(limit)


@router.get("/{comparison_id}.md")
def download_comparison(comparison_id: str):
    row = get_comparison(comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="对比结果不存在")
    return PlainTextResponse(
        row["markdown"],
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="comparison-{comparison_id}.md"'},
    )


@router.get("/{comparison_id}", response_model=ComparisonResponse)
def comparison_detail(comparison_id: str):
    row = get_comparison(comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="对比结果不存在")
    payload = row["payload"] or {}
    if isinstance(payload, dict):
        payload["comparison_id"] = comparison_id
    try:
        return ComparisonResponse.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="对比结果存储格式损坏") from exc
