"""Knowledge-base ingestion, hybrid retrieval and grounded answering."""
from __future__ import annotations

import os
import time
from pathlib import Path

from ..citations import audit_report
from ..evidence import PDFExtractionError, read_pdf_pages
from ..schemas import (
    AnswerRequest,
    AnswerResponse,
    IndexedDocument,
    IndexResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
    SkippedDocument,
)
from ..settings import settings
from ..store import get_document, list_documents
from .chunking import chunk_pages
from .embeddings import EmbeddingError, get_embedder
from .index import KnowledgeIndex, StoredChunk


class RAGError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _make_index() -> KnowledgeIndex:
    embedder = get_embedder()
    return KnowledgeIndex(settings.kb_index_path, embedder.name)


_index = _make_index()


def get_index() -> KnowledgeIndex:
    return _index


def reset_index() -> KnowledgeIndex:
    """Rebuild the process-local index object (used after config changes/tests)."""
    global _index
    _index = _make_index()
    return _index


def _load_pages(document: dict) -> tuple[Path, list[str]]:
    path = settings.paper_dir / document["stored_name"]
    if not path.is_file():
        raise PDFExtractionError("file_missing", f"PDF 文件已丢失: {document['filename']}")
    return path, read_pdf_pages(path)


def _citation_marker(chunk: StoredChunk, *, max_quote: int = 400) -> str:
    quote = " ".join(chunk.text.split())
    if quote and '"' not in quote and len(quote) <= max_quote:
        return f'[[doc:{chunk.document_id} p.{chunk.page} "{quote}"]]'
    return f"[[doc:{chunk.document_id} p.{chunk.page}]]"


def _hit_from_result(result: dict) -> SearchHit:
    chunk: StoredChunk = result["chunk"]
    return SearchHit(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        filename=chunk.filename,
        page=chunk.page,
        text=chunk.text,
        score=round(float(result["score"]), 6),
        vector_score=round(float(result["vector_score"]), 6),
        bm25_score=round(float(result["bm25_score"]), 6),
        rrf_score=round(float(result["rrf_score"]), 6),
        citation=_citation_marker(chunk),
    )


def _resolver():
    cache: dict[str, tuple[dict | None, list[str] | None]] = {}

    def resolve(document_id: str) -> tuple[dict | None, list[str] | None]:
        if document_id in cache:
            return cache[document_id]
        document = get_document(document_id)
        if document is None:
            cache[document_id] = (None, None)
            return cache[document_id]
        try:
            _, pages = _load_pages(document)
            cache[document_id] = (document, pages)
        except PDFExtractionError:
            cache[document_id] = (document, None)
        return cache[document_id]

    return resolve


def _embedding_note() -> str:
    if settings.embedding_backend == "hash":
        return (
            "当前使用 hash 词法哈希嵌入（非语义模型），只能验证检索流程；"
            "不能据此宣称语义检索质量。设置 EMBEDDING_BACKEND=openai 可启用真实 embedding。"
        )
    return f"使用 {settings.embedding_backend} embedding；仍需人工核对引用与语义。"


async def index_documents(document_ids: list[str] | None = None) -> IndexResponse:
    started = time.perf_counter()
    embedder = get_embedder()
    index = get_index()
    index.load()
    if not index.compatible:
        index.clear()

    if document_ids:
        documents = []
        skipped: list[SkippedDocument] = []
        for document_id in document_ids:
            document = get_document(document_id)
            if document is None:
                skipped.append(
                    SkippedDocument(document_id=document_id, filename="?", reason="文档不存在")
                )
            else:
                documents.append(document)
    else:
        documents = list_documents()
        skipped = []

    indexed: list[IndexedDocument] = []
    records: list[StoredChunk] = []
    for document in documents:
        try:
            _, pages = _load_pages(document)
        except PDFExtractionError as exc:
            skipped.append(
                SkippedDocument(
                    document_id=document["document_id"],
                    filename=document["filename"],
                    reason=f"PDF 读取失败: {exc}",
                )
            )
            continue
        if not any(text.strip() for text in pages):
            skipped.append(
                SkippedDocument(
                    document_id=document["document_id"],
                    filename=document["filename"],
                    reason="PDF 未提取到文本（可能需要 OCR）",
                )
            )
            continue
        chunks = chunk_pages(
            document["document_id"],
            pages,
            max_chars=settings.rag_chunk_chars,
            overlap=settings.rag_chunk_overlap,
        )
        if not chunks:
            skipped.append(
                SkippedDocument(
                    document_id=document["document_id"],
                    filename=document["filename"],
                    reason="未生成有效 chunk",
                )
            )
            continue
        try:
            vectors = await embedder.embed([chunk.text for chunk in chunks])
        except EmbeddingError as exc:
            raise RAGError(exc.code, str(exc), retryable=exc.retryable) from exc
        if len(vectors) != len(chunks):
            raise RAGError("embedding_incomplete", "Embedding 数量与 chunk 数量不一致")
        document_records = [
            StoredChunk(
                chunk_id=chunk.chunk_id,
                document_id=document["document_id"],
                filename=document["filename"],
                page=chunk.page,
                text=chunk.text,
                start=chunk.start,
                end=chunk.end,
                vector=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        if document_ids:
            index.add_document(document["document_id"], document["filename"], chunks, vectors)
        else:
            records.extend(document_records)
        indexed.append(
            IndexedDocument(
                document_id=document["document_id"],
                filename=document["filename"],
                page_count=len(pages),
                chunks=len(chunks),
            )
        )

    if not document_ids:
        index.replace_all(records)

    return IndexResponse(
        indexed_documents=indexed,
        skipped=skipped,
        total_chunks=int(index.stats()["total_chunks"]),
        embedding_backend=embedder.name,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


async def search_knowledge(req: SearchRequest) -> SearchResponse:
    started = time.perf_counter()
    index = get_index()
    index.load()
    top_k = min(req.top_k, settings.rag_max_top_k)
    if not index.compatible:
        return SearchResponse(
            query=req.query,
            mode=req.mode,
            embedding_backend=index.embedding_name,
            hits=[],
            elapsed_ms=0,
            note="索引由不同的 embedding 后端构建，请重新索引后再检索。",
        )
    if not index.chunks:
        return SearchResponse(
            query=req.query,
            mode=req.mode,
            embedding_backend=index.embedding_name,
            hits=[],
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            note="知识库为空：请先索引已上传的 PDF。",
        )
    embedder = get_embedder()
    try:
        query_vectors = await embedder.embed([req.query])
    except EmbeddingError as exc:
        raise RAGError(exc.code, str(exc), retryable=exc.retryable) from exc
    results = index.search(
        req.query,
        query_vectors[0],
        mode=req.mode,
        top_k=top_k,
        document_ids=req.document_ids,
        rerank=settings.rerank_backend,
    )
    hits = [_hit_from_result(result) for result in results]
    note = _embedding_note()
    if not hits:
        note += " 未检索到相关片段。"
    return SearchResponse(
        query=req.query,
        mode=req.mode,
        embedding_backend=embedder.name,
        hits=hits,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        note=note,
    )


def _refusal(
    query: str,
    hits: list[SearchHit],
    elapsed_ms: int,
    note: str,
    embedding_backend: str,
) -> AnswerResponse:
    return AnswerResponse(
        query=query,
        answer="知识库中没有找到足够证据回答该问题。请先索引相关 PDF，或换一个更具体的问题。",
        grounded=False,
        refusal=True,
        citations=[],
        hits=hits,
        answer_mode="refusal",
        embedding_backend=embedding_backend,
        elapsed_ms=elapsed_ms,
        note=note or "空检索结果：按设计拒答，不调用模型编造答案。",
    )


def _extractive_answer(hits: list[SearchHit]) -> str:
    lines = ["根据知识库检索到的原文片段（抽取式回答，未调用大模型）：", ""]
    for number, hit in enumerate(hits[:4], 1):
        excerpt = " ".join(hit.text.split())[:500]
        marker = hit.citation
        lines.append(f"{number}. {excerpt} {marker}")
        lines.append("")
    lines.append("> 以上仅为原文摘录；是否回答问题仍需人工判断，引用只完成页码/片段核验。")
    return "\n".join(lines)


async def _llm_answer(query: str, hits: list[SearchHit]) -> tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RAGError("missing_api_key", "缺少 OPENAI_API_KEY", retryable=False)
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        timeout=settings.answer_timeout_seconds,
    )
    context = "\n\n".join(
        f"[S{number}] 文档：{hit.filename} | 页码：{hit.page} | 引用格式：{hit.citation}\n{hit.text}"
        for number, hit in enumerate(hits, 1)
    )
    prompt = (
        "你是科研文献问答助手。只能使用下面给出的 PDF 片段回答，不得使用外部知识补全。"
        "每个事实性结论后必须附上片段中给出的引用标记（[[doc:... p.N]]）。"
        "如果片段不足以回答，明确说“知识库证据不足”，不要猜测。"
        "数字指标必须与片段逐字一致，并说明数据集与训练比例（如果片段有）。"
        "用中文回答，先给结论，再给依据。\n\n"
        f"问题：{query}\n\n片段：\n{context}"
    )
    last_error: Exception | None = None
    for attempt in range(1, 3):
        try:
            response = await client.chat.completions.create(
                model=settings.answer_model,
                messages=[
                    {"role": "system", "content": "你是受证据约束的科研问答助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            content = (response.choices[0].message.content or "").strip()
            if content:
                return content, "llm"
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                import asyncio

                await asyncio.sleep(1.5 * attempt)
    raise RAGError("answer_provider_error", f"LLM 回答失败: {str(last_error)[:300]}", retryable=True)


async def answer_question(req: AnswerRequest) -> AnswerResponse:
    started = time.perf_counter()
    search_response = await search_knowledge(req)
    hits = search_response.hits
    if not hits:
        return _refusal(
            req.query,
            hits,
            search_response.elapsed_ms,
            search_response.note,
            search_response.embedding_backend,
        )
    if settings.rag_min_score and max(hit.score for hit in hits) < settings.rag_min_score:
        return _refusal(
            req.query,
            hits,
            search_response.elapsed_ms,
            f"最高检索分数低于阈值 {settings.rag_min_score}，拒绝生成答案。",
            search_response.embedding_backend,
        )
    if all(hit.bm25_score <= 0 and hit.vector_score <= 0.01 for hit in hits):
        return _refusal(
            req.query,
            hits,
            search_response.elapsed_ms,
            "检索片段与问题的词法/向量重合度过低，拒绝生成答案。",
            search_response.embedding_backend,
        )

    note = search_response.note
    answer_mode = "extractive"
    answer = _extractive_answer(hits)
    if settings.answer_backend == "llm":
        try:
            answer, answer_mode = await _llm_answer(req.query, hits)
        except RAGError as exc:
            answer_mode = "extractive_fallback"
            note += f" LLM 回答失败，已降级为抽取式：{exc}"
    audit = audit_report(answer, _resolver(), skip_claims=answer_mode != "llm")
    if answer_mode == "llm" and audit.verified_local + audit.page_only_local == 0:
        answer = _extractive_answer(hits)
        answer_mode = "extractive_fallback"
        audit = audit_report(answer, _resolver(), skip_claims=True)
        note += " 模型回答未包含可核验引用，已降级为抽取式。"

    elapsed = int((time.perf_counter() - started) * 1000)
    grounded = (
        not audit.unsupported_claims
        and audit.failed_local == 0
        and (audit.verified_local + audit.page_only_local) > 0
    )
    return AnswerResponse(
        query=req.query,
        answer=answer,
        grounded=grounded,
        refusal=False,
        citations=audit.checks,
        hits=hits,
        answer_mode=answer_mode,
        embedding_backend=search_response.embedding_backend,
        elapsed_ms=elapsed,
        note=note,
    )


def knowledge_status() -> dict:
    stats = get_index().stats()
    stats["documents_indexed"] = get_index().documents()
    return stats


def clear_knowledge() -> None:
    get_index().clear()


def remove_document_from_index(document_id: str) -> int:
    return get_index().remove_document(document_id)
