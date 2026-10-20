"""Document upload, listing, page viewing and deletion."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from ..evidence import PDFExtractionError, pdf_page_count, read_pdf_pages, title_hint
from ..rag.service import remove_document_from_index
from ..schemas import DocumentInfo, DocumentPages, PageText
from ..settings import settings
from ..store import (
    add_document,
    delete_document,
    document_count,
    get_document,
    get_document_by_sha,
    list_documents,
)
from .dependencies import require_api_key

router = APIRouter(prefix="/api/v1/documents", tags=["documents"], dependencies=[Depends(require_api_key)])


def _info(row: dict) -> DocumentInfo:
    return DocumentInfo(
        document_id=row["document_id"],
        filename=row["filename"],
        size=row["size"],
        sha256=row.get("sha256"),
        page_count=row.get("page_count"),
        title=row.get("title"),
        created_at=row.get("created_at"),
    )


def _safe_filename(raw: str | None) -> str:
    filename = (raw or "untitled.pdf").replace("\\", "/").split("/")[-1]
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename).strip()
    if len(filename) > settings.max_filename_length:
        stem = Path(filename).stem[: settings.max_filename_length - 4]
        filename = f"{stem}.pdf"
    return filename


@router.post("", response_model=DocumentInfo, status_code=201)
async def upload_document(response: Response, file: UploadFile = File(...)):
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="只接受 .pdf 文件")
    limit = settings.max_upload_mb * 1024 * 1024
    payload = bytearray()
    while chunk := await file.read(64 * 1024):
        payload.extend(chunk)
        if len(payload) > limit:
            raise HTTPException(status_code=413, detail=f"PDF 超过 {settings.max_upload_mb} MB 限制")
    if not payload:
        raise HTTPException(status_code=400, detail="不能上传空文件")
    raw = bytes(payload)
    if b"%PDF-" not in raw[:1024]:
        raise HTTPException(status_code=415, detail="文件缺少 PDF 文件头")
    digest = hashlib.sha256(raw).hexdigest()
    existing = get_document_by_sha(digest)
    if existing is not None:
        response.status_code = 200
        return _info(existing)

    stored_name = f"{uuid4().hex}.pdf"
    path = settings.paper_dir / stored_name
    resolved = path.resolve()
    if settings.paper_dir.resolve() not in resolved.parents:
        raise HTTPException(status_code=500, detail="存储路径校验失败")
    path.write_bytes(raw)
    try:
        pages = read_pdf_pages(path)
        page_count = pdf_page_count(path)
        title = title_hint(pages)
    except PDFExtractionError as exc:
        path.unlink(missing_ok=True)
        status = 422 if exc.code in {"pdf_encrypted", "pdf_unreadable", "pdf_empty"} else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    try:
        document_id = add_document(
            filename=filename,
            size=len(raw),
            stored_name=stored_name,
            sha256=digest,
            page_count=page_count,
            title=title,
        )
    except Exception as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"文档入库失败: {type(exc).__name__}") from exc
    row = get_document(document_id)
    return _info(row or {"document_id": document_id, "filename": filename, "size": len(raw)})


@router.get("", response_model=list[DocumentInfo])
def documents():
    return [_info(row) for row in list_documents()]


@router.get("/{document_id}", response_model=DocumentInfo)
def document_detail(document_id: str):
    row = get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    return _info(row)


@router.get("/{document_id}/pages", response_model=DocumentPages)
def document_pages(document_id: str):
    row = get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    path = settings.paper_dir / row["stored_name"]
    try:
        pages = read_pdf_pages(path)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DocumentPages(
        document_id=document_id,
        filename=row["filename"],
        page_count=row.get("page_count") or len(pages),
        pages=[PageText(page=index, text=text, char_count=len(text)) for index, text in enumerate(pages, 1)],
    )


@router.get("/{document_id}/pages/{page}", response_model=PageText)
def document_page(document_id: str, page: int):
    row = get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    if page < 1:
        raise HTTPException(status_code=422, detail="页码必须大于等于 1")
    path = settings.paper_dir / row["stored_name"]
    try:
        pages = read_pdf_pages(path)
    except PDFExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if page > len(pages):
        total = row.get("page_count") or len(pages)
        raise HTTPException(
            status_code=404,
            detail=f"页码超出可读取范围（PDF 共 {total} 页，本项目最多读取 {len(pages)} 页）",
        )
    text = pages[page - 1]
    return PageText(page=page, text=text, char_count=len(text))


@router.delete("/{document_id}")
def remove_document(document_id: str):
    row = delete_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    path = settings.paper_dir / row["stored_name"]
    path.unlink(missing_ok=True)
    removed_chunks = remove_document_from_index(document_id)
    return {"deleted": document_id, "removed_chunks": removed_chunks, "documents_remaining": document_count()}
