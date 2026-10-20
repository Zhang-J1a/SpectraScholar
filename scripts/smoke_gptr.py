"""Real GPT Researcher smoke test (requires network and valid API keys).

This script never fakes success. If the key, search service, network or upstream
dependency is missing, it exits non-zero with the actual error.

Usage:
    python scripts/smoke_gptr.py --topic "dynamic graph GNN for hyperspectral classification" --source web
    python scripts/smoke_gptr.py --topic "summarize the uploaded papers" --source local
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spectrascholar.research import GPTResearcherBackend, ResearchError  # noqa: E402
from spectrascholar.schemas import ResearchRequest  # noqa: E402
from spectrascholar.settings import settings  # noqa: E402


async def run(args: argparse.Namespace) -> int:
    request = ResearchRequest(
        topic=args.topic,
        source=args.source,
        domain=args.domain,
        language=args.language,
    )
    backend = GPTResearcherBackend()
    settings.ensure_directories()

    async def on_event(level: str, step: str, message: str, duration_ms: int | None = None) -> None:
        print(f"[{level}] {step}: {message}")

    try:
        outcome = await backend.run(f"smoke-{uuid4().hex[:8]}", request, on_event)
    except ResearchError as exc:
        print(f"\nFAILED [{exc.code}] {exc}")
        print("未完成真实 API 联调；不要把本次运行描述为成功。")
        return 1
    except Exception as exc:
        print(f"\nFAILED [{type(exc).__name__}] {exc}")
        return 1

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output = settings.report_dir / f"gptr-smoke-{timestamp}.md"
    output.write_text(outcome.report, encoding="utf-8")
    print("\nREAL API CALL COMPLETED")
    print(f"backend={outcome.backend} demo={outcome.is_demo} chars={len(outcome.report)}")
    print(f"report={output}")
    print("\nPreview:\n" + "\n".join(outcome.report.splitlines()[:15]))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", required=True)
    parser.add_argument("--source", choices=["web", "local"], default="web")
    parser.add_argument("--domain", choices=["hyperspectral", "general"], default="hyperspectral")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
