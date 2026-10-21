"""Reproducible real research-task evaluation.

Runs 10 local-PDF research tasks through the real FastAPI application and the
real GPT Researcher + DeepSeek path, then records status, latency, report size,
citation audit and upstream metadata (costs/sources if provided).

The corpus is the *synthetic* three-PDF fixture. This measures task reliability,
not scientific accuracy on real papers. A Tavily key is not required because
``source=local``; the retriever is DuckDuckGo and may emit warnings if offline.

Usage:
    python scripts/evaluate_research.py
Writes docs/research_runs.json and docs/research_runs.md.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / ".evaluation-research-workspace"
sys.path.insert(0, str(ROOT))

# Configure the isolated workspace and bounded/cheap run before importing app.
os.environ["WORKSPACE_DIR"] = str(WORKSPACE)
os.environ["RESEARCH_BACKEND"] = "gptr"
os.environ["GPTR_RETRIEVER"] = "duckduckgo"
os.environ["GPTR_MAX_ITERATIONS"] = "1"
os.environ["RESEARCH_MAX_ATTEMPTS"] = "1"
os.environ["RESEARCH_TIMEOUT_SECONDS"] = "180"
os.environ["RESEARCH_PHASE_TIMEOUT_SECONDS"] = "150"
os.environ["MAX_CONCURRENT_JOBS"] = "1"
os.environ["RATE_LIMIT_PER_MINUTE"] = "0"
os.environ["API_KEY"] = ""
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ.pop("SPECTRASCHOLAR_SKIP_DOTENV", None)

from fastapi.testclient import TestClient  # noqa: E402

from spectrascholar.main import app  # noqa: E402
from spectrascholar.settings import settings  # noqa: E402
from tests.pdf_factory import (  # noqa: E402
    DYNAMIC_GNN_PAGES,
    HYBRIDSN_PAGES,
    make_pdf_bytes,
    make_table_pdf_bytes,
)

TOPICS = [
    "Compare dynamic graph GNN and HybridSN on Indian Pines under identical 10% training and 9x9 patches.",
    "What OA and Kappa values are reported, and which method do they belong to?",
    "How is the KNN graph constructed and updated during training?",
    "Compare the static RBF graph baseline and the dynamic graph approach.",
    "Does the table agree with the prose? Identify any conflicts.",
    "What are the limitations of ranking the two methods from these numbers?",
    "Summarize the datasets, metrics, and training protocol used.",
    "What model families are used, and what are their inductive biases?",
    "Create a reproducibility checklist for these experiments.",
    "What should a human verify before citing the reported OA numbers?",
]


def _clean_workspace() -> None:
    resolved = WORKSPACE.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"refusing to clean outside project: {resolved}")
    shutil.rmtree(WORKSPACE, ignore_errors=True)
    settings.ensure_directories()


def _write_fixtures() -> None:
    (settings.paper_dir / "dynamic_gnn.pdf").write_bytes(make_pdf_bytes(DYNAMIC_GNN_PAGES))
    (settings.paper_dir / "hybridsn.pdf").write_bytes(make_pdf_bytes(HYBRIDSN_PAGES))
    (settings.paper_dir / "table_paper.pdf").write_bytes(make_table_pdf_bytes())


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[rank]


def _audit_summary(audit: dict | None) -> dict:
    audit = audit or {}
    return {
        "total": audit.get("total", 0),
        "verified_local": audit.get("verified_local", 0),
        "page_only_local": audit.get("page_only_local", 0),
        "failed_local": audit.get("failed_local", 0),
        "external_unchecked": audit.get("external_unchecked", 0),
        "local_file_unverified": audit.get("local_file_unverified", 0),
        "unsupported_claims": len(audit.get("unsupported_claims") or []),
    }


def _run_task(client: TestClient, index: int, topic: str) -> dict:
    started = time.perf_counter()
    response = client.post(
        "/api/v1/research",
        json={"topic": topic, "source": "local", "domain": "hyperspectral", "language": "en"},
    )
    if response.status_code != 202:
        return {
            "index": index,
            "topic": topic,
            "status": "submit_failed",
            "http_status": response.status_code,
            "error": response.text[:500],
            "latency_ms": int((time.perf_counter() - started) * 1000),
        }
    job_id = response.json()["job_id"]
    deadline = time.monotonic() + 240
    job: dict = {}
    while time.monotonic() < deadline:
        job = client.get(f"/api/v1/research/{job_id}").json()
        if job.get("status") in {"completed", "failed", "cancelled"}:
            break
        time.sleep(1)
    events = client.get(f"/api/v1/research/{job_id}/events").json()
    latency_ms = int((time.perf_counter() - started) * 1000)
    metadata = job.get("metadata") or {}
    return {
        "index": index,
        "job_id": job_id,
        "topic": topic,
        "status": job.get("status", "poll_timeout"),
        "error_type": job.get("error_type"),
        "error": job.get("error"),
        "attempts": job.get("attempts", 0),
        "elapsed_ms": job.get("elapsed_ms"),
        "wall_ms": latency_ms,
        "report_chars": len(job.get("report") or ""),
        "is_demo": job.get("is_demo"),
        "backend": job.get("backend"),
        "audit": _audit_summary(job.get("citation_audit")),
        "metadata": metadata,
        "events": len(events),
        "trace_id": job.get("trace_id"),
    }


def main() -> int:
    _clean_workspace()
    _write_fixtures()

    with TestClient(app) as client:
        ids = []
        for name in ("dynamic_gnn.pdf", "hybridsn.pdf", "table_paper.pdf"):
            path = settings.paper_dir / name
            response = client.post(
                "/api/v1/documents",
                files={"file": (name, path.read_bytes(), "application/pdf")},
            )
            response.raise_for_status()
            ids.append(response.json()["document_id"])
        print(f"uploaded {len(ids)} fixture PDFs")

        runs = []
        for index, topic in enumerate(TOPICS, 1):
            print(f"[{index}/{len(TOPICS)}] {topic}")
            run = _run_task(client, index, topic)
            runs.append(run)
            print(
                f"  -> {run.get('status')} report={run.get('report_chars')} chars "
                f"elapsed={run.get('elapsed_ms')}ms"
            )

    completed = [run for run in runs if run.get("status") == "completed"]
    failed = [run for run in runs if run.get("status") not in {"completed"}]
    elapsed_values = [int(run["elapsed_ms"]) for run in completed if run.get("elapsed_ms") is not None]
    costs = [
        float((run.get("metadata") or {}).get("costs") or 0)
        for run in runs
        if isinstance((run.get("metadata") or {}).get("costs"), (int, float))
    ]
    audit_totals = {
        key: sum(run.get("audit", {}).get(key, 0) for run in runs)
        for key in (
            "total",
            "verified_local",
            "page_only_local",
            "failed_local",
            "external_unchecked",
            "local_file_unverified",
            "unsupported_claims",
        )
    }
    summary = {
        "total": len(runs),
        "completed": len(completed),
        "failed": len(failed),
        "success_rate": round(len(completed) / len(runs), 4) if runs else None,
        "latency_p50_ms": _percentile(elapsed_values, 0.50),
        "latency_p95_ms": _percentile(elapsed_values, 0.95),
        "mean_report_chars": round(statistics.mean([r["report_chars"] for r in completed]), 1)
        if completed
        else None,
        "total_costs": round(sum(costs), 6) if costs else None,
        "audit_totals": audit_totals,
        "error_types": sorted({run.get("error_type") for run in failed if run.get("error_type")}),
    }
    output = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": "synthetic_fixture",
        "real_papers": False,
        "source": "local",
        "backend": settings.research_backend,
        "models": {
            "fast": settings.gptr_fast_llm,
            "smart": settings.gptr_smart_llm,
            "strategic": settings.gptr_strategic_llm,
        },
        "retriever": settings.gptr_retriever,
        "max_iterations": settings.gptr_max_iterations,
        "note": (
            "10 个本地合成 PDF 任务，验证真实任务可靠性/状态/耗时/引用审计；"
            "这是本地任务可靠性评测，不是真实论文质量评测；web 任务见 web_research_runs.json。"
        ),
        "documents": ids,
        "summary": summary,
        "tasks": runs,
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "research_runs.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 真实研究任务评测（本地 PDF）",
        "",
        f"- 生成时间：{output['generated_at']}",
        f"- 后端：`{output['backend']}` / `{output['models']['fast']}`",
        f"- 语料：`{output['corpus']}`（不是真实论文）",
        f"- 任务数：{summary['total']}；完成：{summary['completed']}；失败：{summary['failed']}；"
        f"成功率：{summary['success_rate']}",
        f"- 延迟：p50={summary['latency_p50_ms']}ms，p95={summary['latency_p95_ms']}ms",
        f"- 报告平均字符：{summary['mean_report_chars']}",
        f"- 上游 costs 元数据合计：{summary['total_costs']}",
        f"- 引用审计合计：{summary['audit_totals']}",
        "",
        "| # | 状态 | 报告字符 | elapsed_ms | page+ | local_file | unsupported | error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        audit = run.get("audit", {})
        lines.append(
            f"| {run['index']} | {run.get('status')} | {run.get('report_chars', 0)} | "
            f"{run.get('elapsed_ms') or '-'} | {audit.get('page_only_local', 0)} | "
            f"{audit.get('local_file_unverified', 0)} | {audit.get('unsupported_claims', 0)} | "
            f"{run.get('error_type') or ''} |"
        )
    lines += [
        "",
        "> 这是合成夹具上的任务可靠性评测。真实论文质量仍未验证；web 任务见 web_research_runs.md。",
        "",
    ]
    (docs / "research_runs.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n# Research evaluation")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"written: {docs / 'research_runs.json'}")
    return 0 if failed == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
