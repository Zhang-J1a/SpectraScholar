"""Research engine adapters and the background job runner.

GPT Researcher is an upstream Apache-2.0 dependency.  This module only owns the
adapter boundary, per-run configuration, error classification, retries, job
events and citation auditing.  It does not reimplement the upstream search or
report-generation internals.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from .citations import append_audit_section, audit_report
from .domains import build_research_query
from .evidence import PDFExtractionError, read_pdf_pages
from .schemas import ResearchRequest
from .settings import settings
from .store import (
    add_job_event,
    finish_job,
    get_document,
    get_job,
    is_cancel_requested,
    mark_job_running,
)

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, str, str, int | None], Awaitable[None]]


class ResearchError(RuntimeError):
    """A research failure with a stable code and retry decision."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass
class ResearchOutcome:
    report: str
    backend: str
    is_demo: bool
    metadata: dict = field(default_factory=dict)


class ResearchBackend(Protocol):
    name: str

    async def run(
        self,
        job_id: str,
        req: ResearchRequest,
        on_event: EventCallback | None = None,
    ) -> ResearchOutcome: ...


class DemoBackend:
    """Offline demo.  It never claims that web search or an LLM was used."""

    name = "demo"

    async def run(
        self,
        job_id: str,
        req: ResearchRequest,
        on_event: EventCallback | None = None,
    ) -> ResearchOutcome:
        await asyncio.sleep(0)
        if on_event:
            await on_event("info", "demo", "演示模式：未调用搜索服务或大模型")
        report = (
            "# 演示模式：尚未调用真实大模型或检索服务\n\n"
            f"**研究主题**：{req.topic}\n\n"
            f"**资料来源选项**：{req.source}\n\n"
            "这只是一个端到端任务管理演示。设置 `RESEARCH_BACKEND=gptr`，"
            "安装真实研究引擎并配置有效 API Key 后，才能生成真实研究报告。\n\n"
            "> 本报告不是调研结果，不包含任何真实检索来源。\n"
        )
        return ResearchOutcome(
            report=report,
            backend=self.name,
            is_demo=True,
            metadata={"note": "offline demo; no search or LLM call"},
        )


def _mask_secret(text: str) -> str:
    text = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***", text)
    text = re.sub(r"(?i)(api[_-]?key|token)\s*[=:]\s*\S+", r"\1=***", text)
    return text[:1200]


def _classify_exception(exc: Exception) -> ResearchError:
    message = _mask_secret(str(exc))
    name = type(exc).__name__.lower()
    if isinstance(exc, asyncio.TimeoutError) or "timeout" in name:
        return ResearchError("timeout", "研究任务超时", retryable=True)
    if "ratelimit" in name or "429" in message or "rate limit" in message.lower():
        return ResearchError("rate_limited", f"检索或模型 API 触发限流: {message}", retryable=True)
    if "connection" in name or "connect" in message.lower() or "network" in name:
        return ResearchError("network_error", f"外部服务连接失败: {message}", retryable=True)
    if "authentication" in name or "401" in message:
        return ResearchError("auth_error", "模型 API 鉴权失败，请检查密钥", retryable=False)
    if isinstance(exc, ImportError):
        return ResearchError("gptr_import_error", message, retryable=False)
    return ResearchError("research_failed", f"{type(exc).__name__}: {message}", retryable=False)


class GPTResearcherBackend:
    """Adapter around ``gpt_researcher.GPTResearcher`` (verified against 0.16.1)."""

    name = "gptr"

    def _preflight(self, req: ResearchRequest) -> None:
        try:
            from gpt_researcher import GPTResearcher  # noqa: F401
        except ImportError as exc:
            raise ResearchError(
                "gptr_import_error",
                "未安装完整的 gpt-researcher 依赖。请执行 "
                "`pip install -r requirements-live.txt`，并确认依赖安装成功。",
                retryable=False,
            ) from exc

        providers = {
            spec.split(":", 1)[0]
            for spec in (
                settings.gptr_fast_llm,
                settings.gptr_smart_llm,
                settings.gptr_strategic_llm,
            )
            if spec
        }
        required_keys = {
            "openai": "OPENAI_API_KEY",
            "azure_openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        missing_keys = sorted(
            {
                required_keys[provider]
                for provider in providers
                if provider in required_keys and not os.getenv(required_keys[provider])
            }
        )
        if missing_keys and not settings.gptr_allow_missing_key:
            raise ResearchError(
                "missing_api_key",
                f"缺少模型 API 密钥: {', '.join(missing_keys)}。请在 .env 配置，"
                "或使用 RESEARCH_BACKEND=demo。DeepSeek 可使用 provider:model 形式，"
                "例如 deepseek:deepseek-chat，并设置 DEEPSEEK_API_KEY。",
                retryable=False,
            )
        if req.source == "web" and "tavily" in settings.gptr_retriever and not os.getenv("TAVILY_API_KEY"):
            raise ResearchError(
                "missing_search_key",
                "网络研究需要 TAVILY_API_KEY（或改用其它 RETRIEVER）。"
                "没有检索密钥时请使用本地 PDF 模式或 demo 模式。",
                retryable=False,
            )
        if req.source == "local" and not any(settings.paper_dir.glob("*.pdf")):
            raise ResearchError("no_local_pdfs", "本地文献库没有 PDF，请先上传文档", retryable=False)

    def _write_config(self, job_id: str, req: ResearchRequest) -> Path:
        config: dict[str, object] = {
            "REPORT_SOURCE": req.source,
            "DOC_PATH": str(settings.paper_dir),
            "LANGUAGE": "chinese" if req.language == "zh" else "english",
            "MAX_ITERATIONS": settings.gptr_max_iterations,
            "RETRIEVER": settings.gptr_retriever,
        }
        # DeepSeek has no embedding API. If only a DeepSeek key is configured,
        # keep the upstream context filter lexical so research does not try to
        # call OpenAI embeddings implicitly.
        if (
            any(spec.startswith("deepseek:") for spec in (settings.gptr_fast_llm, settings.gptr_smart_llm))
            and not os.getenv("OPENAI_API_KEY")
            and not settings.gptr_embedding
        ):
            config["CONTEXT_FILTER"] = "keyword"
        if settings.gptr_fast_llm:
            config["FAST_LLM"] = settings.gptr_fast_llm
        if settings.gptr_smart_llm:
            config["SMART_LLM"] = settings.gptr_smart_llm
        if settings.gptr_strategic_llm:
            config["STRATEGIC_LLM"] = settings.gptr_strategic_llm
        if settings.gptr_embedding:
            config["EMBEDDING"] = settings.gptr_embedding
        settings.config_dir.mkdir(parents=True, exist_ok=True)
        path = settings.config_dir / f"{job_id}.json"
        path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    async def run(
        self,
        job_id: str,
        req: ResearchRequest,
        on_event: EventCallback | None = None,
    ) -> ResearchOutcome:
        self._preflight(req)

        from gpt_researcher import GPTResearcher

        config_path = self._write_config(job_id, req)
        query = build_research_query(req.topic, req.domain, req.language)
        if on_event:
            await on_event("info", "initialize", "初始化 GPT Researcher（上游 Apache-2.0 引擎）")
        started = time.perf_counter()
        try:
            agent = GPTResearcher(
                query=query,
                report_type=settings.gptr_report_type,
                report_source=req.source,
                report_format="markdown",
                verbose=False,
                config_path=str(config_path),
            )
            if on_event:
                await on_event("info", "conduct_research", "开始检索与阅读来源")
            context = await asyncio.wait_for(
                agent.conduct_research(),
                timeout=settings.research_phase_timeout_seconds,
            )
            empty_context = context is None or (
                isinstance(context, str) and not context.strip()
            ) or (isinstance(context, (list, tuple)) and not any(str(item).strip() for item in context))
            if empty_context:
                raise ResearchError(
                    "empty_context",
                    "研究引擎未返回任何检索上下文（检索失败或来源为空）",
                    retryable=True,
                )
            if on_event:
                await on_event(
                    "info",
                    "write_report",
                    f"检索完成，开始生成报告（上下文 {len(str(context))} 字符）",
                )
            report = await asyncio.wait_for(
                agent.write_report(),
                timeout=settings.research_phase_timeout_seconds,
            )
            if not isinstance(report, str) or not report.strip():
                raise ResearchError("empty_report", "研究引擎返回空报告", retryable=True)
        except (TimeoutError, ResearchError):
            raise
        except Exception as exc:
            raise _classify_exception(exc) from exc
        finally:
            # Keep the JSON config for debugging only when it contains no secrets
            # (it never does), but remove it to avoid unbounded file growth.
            with contextlib.suppress(OSError):
                config_path.unlink(missing_ok=True)

        metadata: dict[str, object] = {
            "context_chars": len(str(context)),
            "elapsed_seconds": round(time.perf_counter() - started, 2),
            "config": {"REPORT_SOURCE": req.source, "RETRIEVER": settings.gptr_retriever},
        }
        for attribute, key in (
            ("get_costs", "costs"),
            ("research_sources", "sources"),
            ("visited_urls", "visited_urls"),
            ("agent", "agent"),
            ("role", "role"),
        ):
            try:
                value = getattr(agent, attribute)
                if callable(value):
                    value = value()
                if key == "visited_urls":
                    value = len(value)
                if key == "sources":
                    value = len(value)
                metadata[key] = value
            except Exception:
                continue
        if on_event:
            await on_event("info", "completed", "GPT Researcher 已返回报告")
        return ResearchOutcome(
            report=report.strip(),
            backend=self.name,
            is_demo=False,
            metadata=metadata,
        )


def _effective_timeout(req: ResearchRequest) -> float:
    requested = req.max_elapsed_seconds or settings.research_timeout_seconds
    return float(
        min(
            requested,
            settings.research_timeout_seconds,
            settings.research_phase_timeout_seconds,
        )
    )


def _extract_cost(metadata: dict | None) -> float | None:
    """Best-effort extraction of upstream cost; never invent a cost."""
    if not metadata:
        return None
    costs = metadata.get("costs")
    if isinstance(costs, (int, float)):
        return float(costs)
    if isinstance(costs, dict):
        for key in ("total_cost", "total", "cost", "cost_usd"):
            value = costs.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    text = json.dumps(costs, ensure_ascii=False) if costs is not None else ""
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    return max((float(number) for number in numbers), default=None)


def get_backend(name: str | None = None) -> ResearchBackend:
    backend = (name or settings.research_backend).lower()
    if backend == "demo":
        return DemoBackend()
    if backend == "gptr":
        return GPTResearcherBackend()
    raise ResearchError("invalid_backend", "RESEARCH_BACKEND 只能取 demo 或 gptr")


def _document_resolver(document_id: str) -> tuple[dict | None, list[str] | None]:
    document = get_document(document_id)
    if document is None:
        return None, None
    path = settings.paper_dir / document["stored_name"]
    if not path.is_file():
        return document, None
    try:
        return document, read_pdf_pages(path)
    except PDFExtractionError:
        return document, None


def _report_header(outcome: ResearchOutcome, req: ResearchRequest, job_id: str, trace_id: str) -> str:
    generated = datetime.now(UTC).isoformat(timespec="seconds")
    engine = (
        "DemoBackend（离线演示，未调用搜索/LLM）"
        if outcome.is_demo
        else "GPT Researcher（Apache-2.0 上游引擎，经 SpectraScholar Adapter 调用）"
    )
    return (
        f"<!-- spectrascholar job={job_id} backend={outcome.backend} is_demo={str(outcome.is_demo).lower()} -->\n"
        f"> 研究引擎：{engine}  \n"
        f"> 任务：`{job_id}` · Trace：`{trace_id}` · 生成时间（UTC）：{generated}  \n"
        f"> 资料模式：`{req.source}` · 领域：`{req.domain}` · 语言：`{req.language}`\n\n"
    )


async def run_research_job(job_id: str, req: ResearchRequest, trace_id: str | None = None) -> None:
    """Execute one queued research job and persist every state transition."""
    job = get_job(job_id)
    if job is None:
        logger.error("research job disappeared job_id=%s", job_id)
        return
    trace_id = trace_id or job.get("trace_id") or job_id
    backend_name = job.get("backend") or settings.research_backend
    if is_cancel_requested(job_id):
        finish_job(job_id, "cancelled", error="用户取消（尚未执行）", error_type="cancelled")
        return

    async def emit(level: str, step: str, message: str, duration_ms: int | None = None) -> None:
        add_job_event(job_id, level, step, message, duration_ms)
        if level == "error":
            logger.error("job=%s trace=%s step=%s %s", job_id, trace_id, step, message)
        else:
            logger.info("job=%s trace=%s step=%s %s", job_id, trace_id, step, message)

    await emit("info", "queued", f"任务入队，后端={backend_name}，trace={trace_id}")

    try:
        backend = get_backend(backend_name)
    except ResearchError as exc:
        finish_job(job_id, "failed", error=str(exc), error_type=exc.code)
        await emit("error", "initialize", str(exc))
        return

    last_error: ResearchError | None = None
    job_started = time.perf_counter()
    total_budget_seconds = min(
        req.max_elapsed_seconds or settings.research_timeout_seconds,
        settings.research_timeout_seconds,
    )
    for attempt in range(1, settings.research_max_attempts + 1):
        if time.perf_counter() - job_started >= total_budget_seconds:
            finish_job(
                job_id,
                "failed",
                error=f"任务超过总时间预算 {total_budget_seconds}s",
                error_type="budget_exceeded",
            )
            await emit("error", "budget_exceeded", "任务超过总时间预算")
            return
        if is_cancel_requested(job_id):
            finish_job(job_id, "cancelled", error="用户取消", error_type="cancelled")
            await emit("warning", "cancelled", "任务在重试前被取消")
            return
        mark_job_running(job_id, attempt)
        await emit("info", "running", f"开始执行（第 {attempt}/{settings.research_max_attempts} 次尝试）")
        started = time.perf_counter()
        try:
            outcome = await asyncio.wait_for(
                backend.run(job_id, req, emit),
                timeout=_effective_timeout(req),
            )
            if is_cancel_requested(job_id):
                finish_job(job_id, "cancelled", error="用户取消", error_type="cancelled")
                await emit("warning", "cancelled", "任务在完成后、审计前被取消")
                return
            if req.max_cost_usd is not None:
                cost = _extract_cost(outcome.metadata)
                if cost is not None and cost > req.max_cost_usd:
                    raise ResearchError(
                        "budget_exceeded",
                        f"上游成本 {cost:.6f} USD 超过预算 {req.max_cost_usd:.6f} USD",
                        retryable=False,
                    )
            await emit(
                "info",
                "audit",
                "开始核验报告中的本地引用与数值性结论",
                int((time.perf_counter() - started) * 1000),
            )
            audit = audit_report(outcome.report, _document_resolver, skip_claims=outcome.is_demo)
            final_report = _report_header(outcome, req, job_id, trace_id) + outcome.report
            final_report = append_audit_section(final_report, audit)
            report_path = settings.report_dir / f"{job_id}.md"
            report_path.write_text(final_report, encoding="utf-8")
            metadata = dict(outcome.metadata)
            metadata["report_path"] = report_path.name
            metadata["backend"] = outcome.backend
            metadata["is_demo"] = outcome.is_demo
            metadata["budget"] = {
                "max_elapsed_seconds": req.max_elapsed_seconds,
                "effective_timeout_seconds": _effective_timeout(req),
                "max_cost_usd": req.max_cost_usd,
                "observed_cost_usd": _extract_cost(outcome.metadata),
            }
            finish_job(
                job_id,
                "completed",
                report=final_report,
                citation_audit=audit.model_dump(mode="json"),
                metadata=metadata,
            )
            elapsed = int((time.perf_counter() - started) * 1000)
            await emit(
                "info",
                "completed",
                f"任务完成，报告 {len(final_report)} 字符，引用核验通过 {audit.verified_local} 条",
                elapsed,
            )
            logger.info("research job completed job_id=%s metadata=%s", job_id, metadata)
            return
        except asyncio.CancelledError:
            finish_job(job_id, "cancelled", error="任务被取消或服务关闭")
            await emit("error", "cancelled", "任务被取消或服务关闭")
            raise
        except ResearchError as exc:
            last_error = exc
        except TimeoutError:
            last_error = ResearchError("timeout", "研究任务超过最大执行时长", retryable=True)
        except Exception as exc:
            last_error = _classify_exception(exc)

        assert last_error is not None
        retryable = last_error.retryable
        if retryable and attempt < settings.research_max_attempts:
            delay = settings.retry_backoff_seconds * attempt
            await emit(
                "warning",
                "retry",
                f"{last_error.code}: {last_error}；{delay:.1f}s 后重试",
            )
            await asyncio.sleep(delay)
            continue
        finish_job(
            job_id,
            "failed",
            error=str(last_error),
            error_type=last_error.code,
        )
        await emit(
            "error",
            "failed",
            f"{last_error.code}: {last_error}（已尝试 {attempt} 次）",
        )
        return
