"""Research engine adapter; original code lives here, GPT Researcher is a dependency."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Protocol

from .domains import build_research_query
from .schemas import ResearchRequest
from .settings import settings
from .store import update_job

logger = logging.getLogger(__name__)


class ResearchBackend(Protocol):
    async def run(self, req: ResearchRequest) -> str: ...


class DemoBackend:
    async def run(self, req: ResearchRequest) -> str:
        # Demo intentionally never pretends to have searched the internet.
        await asyncio.sleep(0)
        return (
            "# 演示模式：尚未调用真实大模型或检索服务\n\n"
            f"**研究主题**：{req.topic}\n\n"
            f"**资料来源选项**：{req.source}\n\n"
            "这只是一个端到端任务管理演示。设置 RESEARCH_BACKEND=gptr，"
            "安装真实研究引擎并配置有效 API Key 后，才能生成真实研究报告。\n"
        )


class GPTResearcherBackend:
    async def run(self, req: ResearchRequest) -> str:
        try:
            from gpt_researcher import GPTResearcher
        except ImportError as exc:
            raise RuntimeError("未安装 gpt-researcher，请先安装 requirements-live.txt") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("缺少 OPENAI_API_KEY，请在 .env 中配置真实的模型 API 密钥")
        if req.source == "local" and not any(settings.paper_dir.glob("*.pdf")):
            raise ValueError("本地文献库没有 PDF，请先上传文档")
        # GPT Researcher's DOC_PATH is read from the process environment.
        os.environ.setdefault("DOC_PATH", str(settings.paper_dir))
        agent = GPTResearcher(
            query=build_research_query(req.topic, req.domain, req.language),
            report_type="research_report",
            report_source=req.source,
            report_format="markdown",
            verbose=False,
        )
        await agent.conduct_research()
        report = await agent.write_report()
        if not isinstance(report, str) or not report.strip():
            raise RuntimeError("研究引擎返回空报告")
        return report


def get_backend() -> ResearchBackend:
    if settings.research_backend == "demo":
        return DemoBackend()
    if settings.research_backend == "gptr":
        return GPTResearcherBackend()
    raise ValueError("RESEARCH_BACKEND 只能取 demo 或 gptr")


async def run_research_job(job_id: str, req: ResearchRequest) -> None:
    update_job(job_id, "running")
    try:
        result = await get_backend().run(req)
        # Basic output handling. Evidence checking is implemented separately for PDFs.
        (settings.report_dir / f"{job_id}.md").write_text(result, encoding="utf-8")
        update_job(job_id, "completed", report=result)
    except Exception as exc:
        logger.exception("Research job failed: %s", job_id)
        update_job(job_id, "failed", error=str(exc)[:1200])
