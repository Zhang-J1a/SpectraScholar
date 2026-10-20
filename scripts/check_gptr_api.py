"""Inspect the installed GPT Researcher public API without making network calls.

Run after installing requirements-live.txt:
    python scripts/check_gptr_api.py
Exit code 2 means the live extra is not fully installed.
"""
from __future__ import annotations

import inspect
import sys

try:
    import gpt_researcher
    from gpt_researcher import GPTResearcher
except ImportError as exc:  # pragma: no cover - depends on optional extra
    print("GPT Researcher 未完整安装或依赖缺失。")
    print(f"原因: {exc}")
    print("请执行: pip install -r requirements-live.txt")
    sys.exit(2)

print("gpt_researcher module:", gpt_researcher.__file__)
for name in ("__init__", "conduct_research", "write_report"):
    try:
        signature = inspect.signature(getattr(GPTResearcher, name))
    except TypeError:
        signature = "<unavailable>"
    print(f"GPTResearcher.{name}{signature}")

from gpt_researcher.config.variables.default import DEFAULT_CONFIG  # noqa: E402

for key in (
    "REPORT_SOURCE",
    "DOC_PATH",
    "RETRIEVER",
    "FAST_LLM",
    "SMART_LLM",
    "STRATEGIC_LLM",
    "EMBEDDING",
    "LANGUAGE",
):
    print(f"{key}={DEFAULT_CONFIG.get(key)!r}")
