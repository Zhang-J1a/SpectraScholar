"""Explicit, resumable-by-inspection workflow for local literature research (P3).

This is deliberately a small state machine, not a second autonomous agent.  Each
node has a typed input/output summary, a timeout, bounded retries and a
persisted status row.  Web research stays inside GPT Researcher; this workflow
owns the local-PDF pipeline that GPT Researcher does not provide.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .citations import append_audit_section, audit_report
from .compare import build_comparison
from .evidence import PDFExtractionError, read_pdf_pages
from .extraction import ExtractionError, evidence_counts, extract_pages
from .rag.service import RAGError, index_documents, search_knowledge
from .schemas import (
    CitationAudit,
    ComparisonResponse,
    PaperExtraction,
    SearchRequest,
    WorkflowRequest,
)
from .settings import settings
from .store import (
    add_workflow_step,
    finish_workflow,
    finish_workflow_step,
    get_document,
    get_workflow,
    mark_workflow_running,
    save_comparison,
    set_workflow_step,
)
from .tools import ArxivSearchError, search_arxiv

logger = logging.getLogger(__name__)

STEPS = ["plan", "screen", "retrieve", "extract", "verify", "compare", "report"]


class WorkflowError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class WorkflowState:
    req: WorkflowRequest
    documents: list[dict] = field(default_factory=list)
    pages: dict[str, list[str]] = field(default_factory=dict)
    papers: list[PaperExtraction] = field(default_factory=list)
    retrieval: list[dict] = field(default_factory=list)
    comparison: ComparisonResponse | None = None
    report: str = ""
    audit: CitationAudit | None = None
    plan: dict = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    arxiv_results: list[dict] = field(default_factory=list)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _load_document(document_id: str) -> tuple[dict, list[str]]:
    document = get_document(document_id)
    if document is None:
        raise WorkflowError("document_missing", f"文档不存在: {document_id}")
    path = settings.paper_dir / document["stored_name"]
    if not path.is_file():
        raise WorkflowError("file_missing", f"PDF 文件已丢失: {document['filename']}")
    try:
        pages = read_pdf_pages(path)
    except PDFExtractionError as exc:
        raise WorkflowError(exc.code, f"PDF 读取失败 ({document['filename']}): {exc}") from exc
    return document, pages


async def _run_arxiv_tool(state: WorkflowState) -> str:
    """Call the arXiv tool from the planning node; failures are non-fatal."""
    arguments = {
        "query": state.req.topic[:500],
        "year_from": state.req.arxiv_year_from,
        "year_to": state.req.arxiv_year_to,
        "task_topic": state.req.topic[:200],
        "max_results": state.req.arxiv_max_results,
    }
    call = {"tool": "arxiv_search", "arguments": arguments, "status": "running"}
    state.tool_calls.append(call)
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(search_arxiv, **arguments),
            timeout=settings.arxiv_timeout_seconds,
        )
        call.update(
            status="completed",
            returned=result.get("returned", 0),
            duplicates_filtered=result.get("duplicates_filtered", 0),
            attempts=result.get("attempts", 1),
        )
        state.arxiv_results = list(result.get("papers", []))
        state.notes.append(f"arXiv 工具返回 {len(state.arxiv_results)} 篇；仅作外部线索，不进入本地证据链。")
        return f"arXiv 工具调用完成，返回 {len(state.arxiv_results)} 篇"
    except TimeoutError:
        call.update(status="failed", error="timeout")
        state.notes.append("arXiv 工具超时；继续本地 PDF 工作流。")
        return "arXiv 工具超时，继续本地流程"
    except ArxivSearchError as exc:
        call.update(status="failed", error=f"{exc.code}: {exc}")
        state.notes.append(f"arXiv 工具失败（{exc.code}）；继续本地 PDF 工作流。")
        return f"arXiv 工具失败（{exc.code}），继续本地流程"
    except Exception as exc:
        call.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        state.notes.append(f"arXiv 工具异常（{type(exc).__name__}）；继续本地 PDF 工作流。")
        return "arXiv 工具异常，继续本地流程"


async def _step_plan(state: WorkflowState) -> str:
    documents = []
    for document_id in state.req.document_ids:
        document, _ = _load_document(document_id)
        documents.append(document)
    if len(documents) < 2:
        raise WorkflowError("not_enough_documents", "至少需要两篇论文")
    state.documents = documents
    state.plan = {
        "dimensions": ["方法/模型", "模型家族", "图构建", "数据集", "指标", "实验条件", "可比性"],
        "source": "local_pdf",
        "steps": STEPS,
        "extraction_mode": state.req.extraction_mode,
    }
    tool_summary = ""
    if "arxiv_search" in state.req.tools:
        tool_summary = "；" + await _run_arxiv_tool(state)
    return (
        f"计划 {len(STEPS)} 个节点，分析 {len(documents)} 篇论文；"
        f"维度：{'、'.join(state.plan['dimensions'])}" + tool_summary
    )


async def _step_screen(state: WorkflowState) -> str:
    readable = 0
    for document in state.documents:
        document_id = document["document_id"]
        try:
            _, pages = _load_document(document_id)
        except WorkflowError as exc:
            state.skipped.append(f"{document['filename']}: {exc}")
            continue
        if not any(text.strip() for text in pages):
            state.skipped.append(f"{document['filename']}: PDF 无文本（可能需要 OCR）")
            continue
        state.pages[document_id] = pages
        readable += 1
    if readable < 2:
        raise WorkflowError(
            "not_enough_readable_papers",
            f"只有 {readable} 篇 PDF 有可提取文本，至少需要 2 篇；扫描件需先 OCR。",
        )
    return f"{readable}/{len(state.documents)} 篇论文有可提取文本" + (
        f"；跳过：{'; '.join(state.skipped)}" if state.skipped else ""
    )


async def _step_retrieve(state: WorkflowState) -> str:
    try:
        index_response = await index_documents(list(state.pages.keys()))
        if index_response.skipped:
            state.notes.append(f"索引跳过 {len(index_response.skipped)} 篇：{index_response.skipped}")
    except RAGError as exc:
        state.notes.append(f"知识库索引失败，继续执行抽取流程：{exc}")
        return "索引失败，跳过检索（不影响抽取/对比）"
    hits: list[dict] = []
    for document_id in state.pages:
        try:
            response = await search_knowledge(
                SearchRequest(
                    query=state.req.topic,
                    top_k=3,
                    document_ids=[document_id],
                    mode="hybrid",
                )
            )
            for hit in response.hits:
                hits.append(hit.model_dump(mode="json"))
        except RAGError as exc:
            state.notes.append(f"检索失败 ({document_id}): {exc}")
    state.retrieval = hits
    return f"检索到 {len(hits)} 条页级证据片段"


async def _step_extract(state: WorkflowState) -> str:
    papers: list[PaperExtraction] = []
    failures: list[str] = []
    for document in state.documents:
        document_id = document["document_id"]
        pages = state.pages.get(document_id)
        if pages is None:
            continue
        try:
            paper = await extract_pages(
                document_id,
                document["filename"],
                pages,
                state.req.extraction_mode,
                pdf_path=settings.paper_dir / document["stored_name"],
            )
            papers.append(paper)
        except ExtractionError as exc:
            failures.append(f"{document['filename']}: {exc.code} {exc}")
    if len(papers) < 2:
        raise WorkflowError(
            "extraction_failed",
            f"成功抽取 {len(papers)} 篇，至少需要 2 篇；失败：{failures or '无'}",
        )
    state.papers = papers
    mode = papers[0].extraction_mode
    return f"抽取 {len(papers)} 篇（模式 {mode}）；失败 {len(failures)} 篇"


async def _step_verify(state: WorkflowState) -> str:
    per_paper = []
    total = verified = rejected = 0
    for paper in state.papers:
        counts = evidence_counts(paper)
        total += counts["evidence_total"]
        verified += counts["evidence_verified"]
        rejected += counts["rejected"]
        per_paper.append({"document_id": paper.document_id, "filename": paper.filename, **counts})
    state.verification = {
        "evidence_total": total,
        "evidence_verified": verified,
        "rejected": rejected,
        "papers": per_paper,
    }
    if total == 0 or verified == 0:
        raise WorkflowError(
            "no_verified_evidence",
            "没有获得任何通过原文核验的证据；拒绝生成看似有依据的报告。",
        )
    return f"证据核验：{verified}/{total} 通过，丢弃 {rejected} 个候选"


async def _step_compare(state: WorkflowState) -> str:
    comparison = build_comparison(
        state.papers,
        extraction_mode=state.papers[0].extraction_mode if state.papers else "heuristic",
        language=state.req.language,
    )
    comparison_id = save_comparison(
        [paper.document_id for paper in state.papers],
        comparison.extraction_mode,
        comparison.model_dump(mode="json"),
        comparison.markdown,
    )
    state.comparison = comparison.model_copy(update={"comparison_id": comparison_id})
    return (
        f"对比 {len(state.papers)} 篇：{len(comparison.metric_rows)} 条指标，"
        f"{len(comparison.comparability_issues)} 条不可比提示"
    )


def _workflow_resolver(state: WorkflowState):
    by_id = {document["document_id"]: document for document in state.documents}
    cache: dict[str, list[str] | None] = {}

    def resolve(document_id: str):
        document = by_id.get(document_id) or get_document(document_id)
        if document is None:
            return None, None
        if document_id not in cache:
            if document_id in state.pages:
                cache[document_id] = state.pages[document_id]
            else:
                try:
                    _, cache[document_id] = _load_document(document_id)
                except WorkflowError:
                    cache[document_id] = None
        return document, cache[document_id]

    return resolve


def _compose_report(state: WorkflowState) -> str:
    assert state.comparison is not None
    generated = _utcnow()
    lines = [
        f"<!-- spectrascholar workflow={state.req.idempotency_key or 'local'} source=local_pdf -->",
        "> 工作流：`plan → screen → retrieve → extract → verify → compare → report`  ",
        f"> 生成时间（UTC）：{generated} · 抽取模式：`{state.comparison.extraction_mode}`  ",
        "> 说明：本报告由本地 PDF 流水线生成，不调用网页搜索；通用网页研究请使用 GPT Researcher 模式。",
        "",
        "# 科研文献调研报告",
        "",
        f"**研究问题**：{state.req.topic}",
        "",
        "## 任务规划",
        "",
        f"- 分析维度：{'、'.join(state.plan.get('dimensions', []))}",
        f"- 参与论文：{len(state.papers)} 篇",
        f"- 证据核验：{state.verification.get('evidence_verified', 0)}/"
        f"{state.verification.get('evidence_total', 0)} 通过",
    ]
    if state.skipped:
        lines.append(f"- 跳过文档：{'; '.join(state.skipped)}")
    if state.notes:
        lines.append(f"- 运行提示：{'; '.join(state.notes)}")
    if state.tool_calls:
        lines += ["", "## 外部工具调用（arXiv）", ""]
        for call in state.tool_calls:
            args = call.get("arguments", {})
            detail = (
                f"`{call['tool']}` status={call.get('status')} "
                f"returned={call.get('returned', 0)} query={args.get('query', '')}"
            )
            if call.get("error"):
                detail += f" error={call['error']}"
            lines.append(f"- {detail}")
        for paper in state.arxiv_results[:5]:
            lines.append(
                f"- [{paper.get('title')}]({paper.get('entry_url')}) "
                f"({paper.get('year')}, DOI: {paper.get('doi') or 'n/a'})"
            )
        lines += [
            "",
            "> 外部检索只用于发现问题，**不进入本地 PDF 证据链，也不参与可比组/排名**。",
            "",
        ]
    lines += ["", state.comparison.markdown, ""]

    if state.retrieval:
        lines += ["## 检索命中的相关原文", ""]
        for index, hit in enumerate(state.retrieval[:10], 1):
            citation = hit["citation"]
            excerpt = " ".join(hit["text"].split())[:400]
            lines.append(f"{index}. **{hit['filename']} p.{hit['page']}**：{excerpt} {citation}")
        lines.append("")

    lines += [
        "## 工作流边界",
        "",
        "- 本工作流只处理已上传的本地 PDF，不执行网页检索；网页检索由 GPT Researcher 适配层负责。",
        "- 抽取值只有在页码与原文片段匹配后才保留；原文出现不代表事实语义正确。",
        "- 指标排名仅在数据集、指标、训练比例、补丁尺寸、协议全部一致时生成。",
        "- 未实现断点恢复：失败任务保留节点状态，需要重新提交；不会伪造已完成节点。",
        "",
    ]
    return "\n".join(lines)


async def _step_report(state: WorkflowState) -> str:
    report = _compose_report(state)
    audit = audit_report(report, _workflow_resolver(state))
    state.audit = audit
    state.report = append_audit_section(report, audit)
    return (
        f"报告 {len(state.report)} 字符；本地引用通过 {audit.verified_local} 条，"
        f"失败 {audit.failed_local} 条，缺引用数值结论 {len(audit.unsupported_claims)} 条"
    )


STEP_FUNCTIONS = {
    "plan": _step_plan,
    "screen": _step_screen,
    "retrieve": _step_retrieve,
    "extract": _step_extract,
    "verify": _step_verify,
    "compare": _step_compare,
    "report": _step_report,
}


async def _execute_step(workflow_id: str, name: str, state: WorkflowState) -> str:
    set_workflow_step(workflow_id, name)
    step_id = add_workflow_step(
        workflow_id,
        name,
        "running",
        attempt=1,
        input_summary=f"task={name}",
        started_at=_utcnow(),
    )
    started = time.perf_counter()
    max_attempts = settings.workflow_max_retries + 1
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            summary = await asyncio.wait_for(
                STEP_FUNCTIONS[name](state),
                timeout=settings.workflow_step_timeout_seconds,
            )
            finish_workflow_step(
                step_id,
                "completed",
                output_summary=summary[:1000],
                duration_ms=int((time.perf_counter() - started) * 1000),
                attempt=attempt,
            )
            return summary
        except TimeoutError:
            last_error = WorkflowError(
                "step_timeout",
                f"节点 {name} 超过 {settings.workflow_step_timeout_seconds}s",
            )
        except WorkflowError as exc:
            last_error = exc
        except Exception as exc:
            last_error = WorkflowError("step_failed", f"{type(exc).__name__}: {exc}")
        if attempt < max_attempts:
            await asyncio.sleep(0.5 * attempt)
    message = str(last_error)
    finish_workflow_step(
        step_id,
        "failed",
        error=message[:1000],
        duration_ms=int((time.perf_counter() - started) * 1000),
        attempt=max_attempts,
    )
    raise WorkflowError(
        getattr(last_error, "code", "step_failed"),
        f"节点 {name} 失败：{message}",
    )


async def run_workflow_job(workflow_id: str, req: WorkflowRequest) -> None:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        logger.error("workflow disappeared workflow_id=%s", workflow_id)
        return
    mark_workflow_running(workflow_id)
    state = WorkflowState(req=req)
    try:
        for name in STEPS:
            await _execute_step(workflow_id, name, state)
        assert state.comparison is not None and state.audit is not None
        finish_workflow(
            workflow_id,
            "completed",
            report=state.report,
            comparison_id=state.comparison.comparison_id,
            citation_audit=state.audit.model_dump(mode="json"),
        )
        logger.info("workflow completed workflow_id=%s", workflow_id)
    except asyncio.CancelledError:
        finish_workflow(workflow_id, "cancelled", error="任务被取消或服务关闭")
        raise
    except WorkflowError as exc:
        finish_workflow(workflow_id, "failed", error=f"{exc.code}: {exc}")
        logger.error("workflow failed workflow_id=%s code=%s error=%s", workflow_id, exc.code, exc)
    except Exception as exc:
        finish_workflow(workflow_id, "failed", error=f"{type(exc).__name__}: {exc}"[:1200])
        logger.exception("workflow crashed workflow_id=%s", workflow_id)
