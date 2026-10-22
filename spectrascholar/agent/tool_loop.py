"""Bounded autonomous tool loop.

The planner is an LLM that chooses one of a closed set of tools or finishes.
It is deliberately bounded: max steps, allowed tools, per-tool errors and a
forced final answer.  No tool result is treated as a local PDF evidence quote.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ..llm_config import LLMConfigurationError, resolve_llm_credentials
from ..rag.service import search_knowledge
from ..schemas import SearchRequest
from ..settings import settings
from ..tools import ArxivSearchError, search_arxiv


class ToolLoopError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ToolObservation:
    step: int
    tool: str
    arguments: dict[str, Any]
    status: str
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ToolLoopResult:
    query: str
    answer: str
    stopped_reason: str
    observations: list[ToolObservation] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0


Planner = Callable[[str, list[ToolObservation], list[str], int, bool], Awaitable[dict[str, Any]]]
Executor = Callable[[str, dict[str, Any], str], Awaitable[dict[str, Any]]]

TOOL_DESCRIPTIONS = {
    "arxiv_search": (
        "Search arXiv for external papers. Arguments: query (string), "
        "year_from (int|null), year_to (int|null), task_topic (string|null), max_results (1-10)."
    ),
    "local_search": (
        "Search the local indexed PDF knowledge base. Arguments: query (string), top_k (1-10)."
    ),
}


def _parse_plan(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            from json_repair import repair_json

            payload = json.loads(repair_json(cleaned))
        except Exception as exc:  # pragma: no cover - defensive
            raise ToolLoopError("invalid_plan", f"planner 未返回 JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ToolLoopError("invalid_plan", "planner 返回值必须是 JSON object")
    return payload


def _prompt(
    query: str,
    observations: list[ToolObservation],
    allowed_tools: list[str],
    step: int,
    force_finish: bool,
) -> str:
    tools = "\n".join(f"- {name}: {TOOL_DESCRIPTIONS[name]}" for name in allowed_tools)
    history = [
        {
            "step": item.step,
            "tool": item.tool,
            "arguments": item.arguments,
            "status": item.status,
            "error": item.error,
            "result": item.result,
        }
        for item in observations
    ]
    action = (
        "You must finish now; do not call another tool."
        if force_finish
        else "Choose one tool call or finish."
    )
    return (
        f"User question: {query}\n"
        f"Allowed tools:\n{tools}\n"
        f"Previous observations:\n{json.dumps(history, ensure_ascii=False)[:6000]}\n"
        f"Step: {step}.\n{action}\n"
        "Return ONLY JSON with one of these shapes:\n"
        '{"action":"tool_call","tool":"<name>","arguments":{...},"reason":"..."}\n'
        '{"action":"finish","answer":"...","reason":"..."}\n'
        "Do not invent tool names. Do not claim local PDF evidence from web/arXiv results."
    )


async def _default_planner(
    query: str,
    observations: list[ToolObservation],
    allowed_tools: list[str],
    step: int,
    force_finish: bool,
) -> dict[str, Any]:
    try:
        credentials = resolve_llm_credentials()
    except LLMConfigurationError as exc:
        raise ToolLoopError("missing_api_key", str(exc)) from exc
    assert credentials is not None
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=credentials.api_key,
        base_url=credentials.base_url,
        timeout=settings.agent_timeout_seconds,
    )
    response = await client.chat.completions.create(
        model=settings.agent_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a bounded research tool planner. Use tools only when needed. "
                    "Return strict JSON only. Never fabricate citations."
                ),
            },
            {
                "role": "user",
                "content": _prompt(query, observations, allowed_tools, step, force_finish),
            },
        ],
        temperature=0,
    )
    content = response.choices[0].message.content or ""
    return _parse_plan(content)


async def _default_executor(tool: str, arguments: dict[str, Any], original_query: str) -> dict[str, Any]:
    if tool == "arxiv_search":
        query = str(arguments.get("query") or original_query)[:500]
        result = await asyncio.wait_for(
            asyncio.to_thread(
                search_arxiv,
                query,
                year_from=arguments.get("year_from"),
                year_to=arguments.get("year_to"),
                task_topic=arguments.get("task_topic"),
                max_results=min(max(int(arguments.get("max_results", 5)), 1), 10),
            ),
            timeout=settings.arxiv_timeout_seconds,
        )
        return {
            "returned": result.get("returned", 0),
            "papers": [
                {
                    "title": paper.get("title"),
                    "year": paper.get("year"),
                    "doi": paper.get("doi"),
                    "entry_url": paper.get("entry_url"),
                }
                for paper in result.get("papers", [])
            ],
        }
    if tool == "local_search":
        query = str(arguments.get("query") or original_query)[:500]
        result = await search_knowledge(
            SearchRequest(
                query=query,
                top_k=min(max(int(arguments.get("top_k", 5)), 1), 10),
            )
        )
        return {
            "hits": [
                {
                    "document_id": hit.document_id,
                    "filename": hit.filename,
                    "page": hit.page,
                    "text": hit.text[:1000],
                    "citation": hit.citation,
                    "score": hit.score,
                }
                for hit in result.hits
            ],
            "note": result.note,
        }
    raise ToolLoopError("unknown_tool", f"未知工具: {tool}")


async def run_tool_loop(
    query: str,
    *,
    max_steps: int | None = None,
    allowed_tools: list[str] | None = None,
    planner: Planner | None = None,
    executor: Executor | None = None,
) -> ToolLoopResult:
    query = query.strip()
    if not query:
        raise ToolLoopError("invalid_query", "query 不能为空")
    allowed = list(allowed_tools or ["arxiv_search", "local_search"])
    allowed = [name for name in allowed if name in TOOL_DESCRIPTIONS]
    if not allowed:
        raise ToolLoopError("no_tools", "没有可用工具")
    limit = max(1, min(max_steps or settings.agent_max_steps, 5))
    plan_fn = planner or _default_planner
    execute_fn = executor or _default_executor
    observations: list[ToolObservation] = []
    sources: list[dict[str, Any]] = []

    for step in range(1, limit + 1):
        try:
            plan = await asyncio.wait_for(
                plan_fn(query, observations, allowed, step, False),
                timeout=settings.agent_timeout_seconds,
            )
        except ToolLoopError:
            raise
        except Exception as exc:
            raise ToolLoopError("planner_failed", f"{type(exc).__name__}: {exc}") from exc

        action = str(plan.get("action", "")).lower()
        if action == "finish":
            answer = str(plan.get("answer") or "").strip()
            if answer:
                return ToolLoopResult(
                    query=query,
                    answer=answer,
                    stopped_reason="planner_finish",
                    observations=observations,
                    sources=sources,
                    steps=step,
                )
            continue
        if action != "tool_call":
            observations.append(
                ToolObservation(
                    step=step,
                    tool="",
                    arguments={},
                    status="error",
                    error="planner 返回未知 action",
                )
            )
            continue
        tool = str(plan.get("tool", ""))
        if tool not in allowed:
            observations.append(
                ToolObservation(
                    step=step,
                    tool=tool or "unknown",
                    arguments={},
                    status="error",
                    error="工具不在 allowed_tools 中",
                )
            )
            continue
        arguments = plan.get("arguments")
        if not isinstance(arguments, dict):
            arguments = {}
        try:
            result = await asyncio.wait_for(
                execute_fn(tool, arguments, query),
                timeout=settings.agent_timeout_seconds,
            )
            observation = ToolObservation(
                step=step,
                tool=tool,
                arguments=arguments,
                status="completed",
                result=result,
            )
            observations.append(observation)
            if tool == "arxiv_search":
                for paper in result.get("papers", []):
                    sources.append(
                        {
                            "kind": "arxiv",
                            "title": paper.get("title"),
                            "url": paper.get("entry_url"),
                            "doi": paper.get("doi"),
                        }
                    )
            elif tool == "local_search":
                for hit in result.get("hits", []):
                    sources.append(
                        {
                            "kind": "local_pdf",
                            "document_id": hit.get("document_id"),
                            "filename": hit.get("filename"),
                            "page": hit.get("page"),
                            "citation": hit.get("citation"),
                        }
                    )
        except (ArxivSearchError, ToolLoopError) as exc:
            observations.append(
                ToolObservation(
                    step=step,
                    tool=tool,
                    arguments=arguments,
                    status="error",
                    error=str(exc),
                )
            )
        except Exception as exc:
            observations.append(
                ToolObservation(
                    step=step,
                    tool=tool,
                    arguments=arguments,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    # Bounded loop exhausted: force a final answer from observations.
    try:
        final = await asyncio.wait_for(
            plan_fn(query, observations, [], limit + 1, True),
            timeout=settings.agent_timeout_seconds,
        )
        answer = str(final.get("answer") or "").strip()
    except Exception:
        answer = ""
    if not answer:
        answer = (
            "工具调用达到上限，未能得到可靠结论。"
            f"已执行 {len(observations)} 次工具观察；请缩小问题或增加步骤上限。"
        )
    return ToolLoopResult(
        query=query,
        answer=answer,
        stopped_reason="max_steps",
        observations=observations,
        sources=sources,
        steps=len(observations),
    )
