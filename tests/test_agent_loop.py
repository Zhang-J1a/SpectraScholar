from __future__ import annotations

import asyncio

from spectrascholar.agent import ToolLoopResult, run_tool_loop
from spectrascholar.agent.tool_loop import ToolObservation


def _planner(plans):
    async def plan(query, observations, allowed_tools, step, force_finish):
        return plans.pop(0)

    return plan


def _executor(calls):
    async def execute(tool, arguments, query):
        calls.append((tool, arguments))
        return {"papers": [{"title": "Tool paper", "entry_url": "https://example.test/p"}]}

    return execute


def test_tool_loop_calls_tool_then_finishes():
    calls: list[tuple[str, dict]] = []
    result = asyncio.run(
        run_tool_loop(
            "find hyperspectral papers",
            max_steps=3,
            planner=_planner(
                [
                    {
                        "action": "tool_call",
                        "tool": "arxiv_search",
                        "arguments": {"query": "hyperspectral"},
                    },
                    {"action": "finish", "answer": "found one paper"},
                ]
            ),
            executor=_executor(calls),
        )
    )
    assert result.answer == "found one paper"
    assert result.stopped_reason == "planner_finish"
    assert result.steps == 2
    assert calls == [("arxiv_search", {"query": "hyperspectral"})]
    assert result.sources[0]["kind"] == "arxiv"


def test_tool_loop_is_bounded_and_rejects_unknown_tool():
    calls: list[tuple[str, dict]] = []

    result = asyncio.run(
        run_tool_loop(
            "bounded query",
            max_steps=2,
            allowed_tools=["arxiv_search"],
            planner=_planner(
                [
                    {"action": "tool_call", "tool": "not_allowed", "arguments": {}},
                    {"action": "tool_call", "tool": "arxiv_search", "arguments": {}},
                ]
            ),
            executor=_executor(calls),
        )
    )
    assert result.stopped_reason == "max_steps"
    assert result.steps == 2
    assert result.observations[0].status == "error"
    assert calls == [("arxiv_search", {})]


def test_agent_loop_endpoint_returns_observation(client, monkeypatch):
    import spectrascholar.api.tools as tools_api

    async def fake_loop(query, **kwargs):
        return ToolLoopResult(
            query=query,
            answer="done",
            stopped_reason="planner_finish",
            observations=[
                ToolObservation(
                    step=1,
                    tool="arxiv_search",
                    arguments={"query": query},
                    status="completed",
                    result={"papers": []},
                )
            ],
            sources=[],
            steps=1,
        )

    monkeypatch.setattr(tools_api, "run_tool_loop", fake_loop)
    response = client.post(
        "/api/v1/tools/agent_loop",
        json={"query": "find papers", "max_steps": 2},
    )
    assert response.status_code == 200, response.text
    assert response.json()["answer"] == "done"
    assert response.json()["observations"][0]["tool"] == "arxiv_search"
