"""FastAPI API and a lightweight single-page interface."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from .evidence import heuristic_extract, llm_extract, read_pdf_pages
from .research import run_research_job
from .schemas import (
    CompareRequest, ComparisonResponse, DocumentInfo, JobDetails,
    JobSubmitted, ResearchRequest,
)
from .settings import settings
from .store import (
    add_document, create_job, get_document, get_job, init_store,
    list_documents, recent_jobs,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_store()
    yield


app = FastAPI(title="SpectraScholar", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(settings.root / "web" / "index.html")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "research_backend": settings.research_backend,
            "extractor_backend": settings.extractor_backend}


@app.post("/api/v1/research", response_model=JobSubmitted, status_code=202)
async def start_research(req: ResearchRequest, tasks: BackgroundTasks):
    if req.source == "local" and not list_documents():
        raise HTTPException(status_code=400, detail="请先上传论文 PDF，再选择本地文档调研")
    job_id = create_job(req)
    tasks.add_task(run_research_job, job_id, req)
    return JobSubmitted(job_id=job_id, status="queued")


@app.get("/api/v1/research", response_model=list[JobDetails])
def research_history(limit: int = 20):
    return recent_jobs(limit)


@app.get("/api/v1/research/{job_id}", response_model=JobDetails)
def research_result(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.get("/api/v1/reports/{job_id}.md")
def download_report(job_id: str):
    job = get_job(job_id)
    if not job or job["status"] != "completed":
        raise HTTPException(status_code=404, detail="报告不存在或尚未完成")
    return PlainTextResponse(job["report"], media_type="text/markdown; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{job_id}.md"'})


@app.post("/api/v1/documents", response_model=DocumentInfo, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    # Read one byte beyond maximum to reject huge files before persisting them.
    raw = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    filename = (file.filename or "unnamed.pdf").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".pdf") or not raw.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="只接受具有 PDF 文件头的 .pdf 文件")
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF 文件过大")
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")
    stored_name = f"{uuid4().hex}.pdf"
    path = settings.paper_dir / stored_name
    path.write_bytes(raw)
    doc_id = add_document(filename, len(raw), stored_name)
    return DocumentInfo(document_id=doc_id, filename=filename, size=len(raw))


@app.get("/api/v1/documents", response_model=list[DocumentInfo])
def documents():
    return list_documents()


@app.post("/api/v1/compare", response_model=ComparisonResponse)
async def compare_papers(req: CompareRequest):
    papers = []
    for doc_id in req.document_ids:
        doc = get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"找不到论文: {doc_id}")
        path = settings.paper_dir / doc["stored_name"]
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"论文文件已丢失: {doc_id}")
        try:
            pages = read_pdf_pages(path)
            if settings.extractor_backend == "heuristic":
                out = heuristic_extract(doc_id, doc["filename"], pages)
            elif settings.extractor_backend == "llm":
                out = await llm_extract(doc_id, doc["filename"], pages)
            else:
                raise ValueError("EXTRACTOR_BACKEND 只能是 heuristic 或 llm")
            papers.append(out)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"PDF 抽取失败 ({doc['filename']}): {exc}") from exc
    return ComparisonResponse(papers=papers, extraction_mode=settings.extractor_backend)
