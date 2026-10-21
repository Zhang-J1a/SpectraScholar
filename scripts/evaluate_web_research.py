"""P4.2: reproducible real web-research evaluation.

Runs N real ``source=web`` tasks through the FastAPI app, GPT Researcher,
Tavily and DeepSeek. Records completion, failures, latency, report size,
source count, upstream costs and citation-audit counts.

The current Windows sandbox maps public hosts to 198.18.0.x. Upstream blocks
those as private addresses, so ``--allow-private`` is required *in this
sandbox only*. It disables the upstream SSRF guard; never use it on a public
server.

Usage:
    python scripts/evaluate_web_research.py --limit 10 --allow-private
"""
from __future__ import annotations

import argparse
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
WORKSPACE = ROOT / ".evaluation-web-workspace"
sys.path.insert(0, str(ROOT))

TOPICS = [
    "What OA and Kappa does HybridSN report on Indian Pines, and under what training ratio and patch size?",
    "What accuracy does SSRN report for Indian Pines hyperspectral classification, and under what protocol?",
    "What OA does a graph convolutional network (GCN) report on Indian Pines, and how is its graph constructed?",
    "Compare spectral-spatial transformer methods for hyperspectral image classification on Indian Pines and Pavia University.",
    "Describe the Indian Pines dataset: classes, spatial size, spectral bands, and standard train/test splits.",
    "What are the standard evaluation metrics (OA, AA, Kappa) for hyperspectral image classification, and how are they defined?",
    "How does training-sample ratio affect hyperspectral classification accuracy on Indian Pines?",
    "Compare KNN graph construction and RBF/superpixel graphs for GCN-based hyperspectral classification.",
    "What data leakage and reproducibility risks appear in hyperspectral image classification benchmarks?",
    "What should a researcher verify before citing an OA number from a hyperspectral classification paper?",
]


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


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[rank]


def _clean_workspace() -> None:
    resolved = WORKSPACE.resolve()
    if ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"refusing to clean outside project: {resolved}")
    shutil.rmtree(WORKSPACE, ignore_errors=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)


def _write_output(payload: dict) -> None:
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "web_research_runs.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# 真实网页研究评测（Tavily）",
        "",
        f"- 生成时间：{payload['generated_at']}",
        f"- 后端：`{payload['backend']}` / `{payload['models']['fast']}`",
        f"- 检索器：`{payload['retriever']}`",
        f"- 任务数：{summary['total']}；完成：{summary['completed']}；失败：{summary['failed']}；"
        f"成功率：{summary['success_rate']}",
        f"- 延迟：p50={summary['latency_p50_ms']}ms，p95={summary['latency_p95_ms']}ms",
        f"- 报告平均字符：{summary['mean_report_chars']}",
        f"- 上游 costs 合计：{summary['total_costs']}",
        f"- 来源总数：{summary['total_sources']}",
        f"- 引用审计合计：{summary['audit_totals']}",
        "",
        "| # | 状态 | 报告字符 | elapsed_ms | sources | 外部链接 | 缺引用 | error |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for run in payload["tasks"]:
        audit = run.get("audit", {})
        meta = run.get("metadata") or {}
        lines.append(
            f"| {run['index']} | {run.get('status')} | {run.get('report_chars', 0)} | "
            f"{run.get('elapsed_ms') or '-'} | {meta.get('sources', '-')} | "
            f"{audit.get('external_unchecked', 0)} | {audit.get('unsupported_claims', 0)} | "
            f"{run.get('error_type') or ''} |"
        )
    lines += [
        "",
        "> 这是当前网络代理环境下的真实网页任务评测；外部链接未做内容核验。",
        "> `ALLOW_PRIVATE_URLS=true` 仅用于本地代理环境，会关闭 SSRF 防护，不能用于生产。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--allow-private", action="store_true")
    args = parser.parse_args()
    limit = max(1, min(args.limit, len(TOPICS)))

    os.environ["WORKSPACE_DIR"] = str(WORKSPACE)
    os.environ["RESEARCH_BACKEND"] = "gptr"
    os.environ["GPTR_RETRIEVER"] = "tavily"
    os.environ["GPTR_MAX_ITERATIONS"] = "1"
    os.environ["RESEARCH_MAX_ATTEMPTS"] = "1"
    os.environ["RESEARCH_TIMEOUT_SECONDS"] = "300"
    os.environ["RESEARCH_PHASE_TIMEOUT_SECONDS"] = "240"
    os.environ["MAX_CONCURRENT_JOBS"] = "1"
    os.environ["RATE_LIMIT_PER_MINUTE"] = "0"
    os.environ["API_KEY"] = ""
    os.environ["LOG_LEVEL"] = "WARNING"
    if args.allow_private:
        os.environ["ALLOW_PRIVATE_URLS"] = "true"
    os.environ.pop("SPECTRASCHOLAR_SKIP_DOTENV", None)

    from fastapi.testclient import TestClient

    from spectrascholar.main import app
    from spectrascholar.settings import settings

    _clean_workspace()
    settings.ensure_directories()

    runs: list[dict] = []
    with TestClient(app) as client:
        for index, topic in enumerate(TOPICS[:limit], 1):
            print(f"[{index}/{limit}] {topic}")
            started = time.perf_counter()
            response = client.post(
                "/api/v1/research",
                json={"topic": topic, "source": "web", "domain": "hyperspectral", "language": "en"},
            )
            if response.status_code != 202:
                run = {
                    "index": index,
                    "topic": topic,
                    "status": "submit_failed",
                    "http_status": response.status_code,
                    "error": response.text[:500],
                    "wall_ms": int((time.perf_counter() - started) * 1000),
                }
                runs.append(run)
                print(f"  -> submit_failed {response.status_code}")
                _write_output({"tasks": runs, "summary": {}})
                continue
            job_id = response.json()["job_id"]
            deadline = time.monotonic() + 330
            job: dict = {}
            while time.monotonic() < deadline:
                job = client.get(f"/api/v1/research/{job_id}").json()
                if job.get("status") in {"completed", "failed", "cancelled"}:
                    break
                time.sleep(1)
            events = client.get(f"/api/v1/research/{job_id}/events").json()
            audit = _audit_summary(job.get("citation_audit"))
            metadata = job.get("metadata") or {}
            run = {
                "index": index,
                "job_id": job_id,
                "topic": topic,
                "status": job.get("status", "poll_timeout"),
                "error_type": job.get("error_type"),
                "error": job.get("error"),
                "attempts": job.get("attempts", 0),
                "elapsed_ms": job.get("elapsed_ms"),
                "wall_ms": int((time.perf_counter() - started) * 1000),
                "report_chars": len(job.get("report") or ""),
                "is_demo": job.get("is_demo"),
                "backend": job.get("backend"),
                "audit": audit,
                "metadata": metadata,
                "events": len(events),
                "trace_id": job.get("trace_id"),
            }
            runs.append(run)
            print(
                f"  -> {run['status']} report={run['report_chars']} chars "
                f"elapsed={run['elapsed_ms']}ms sources={metadata.get('sources')}"
            )
            _write_output({"tasks": runs, "summary": {}})

    completed = [run for run in runs if run.get("status") == "completed"]
    failed = [run for run in runs if run.get("status") != "completed"]
    elapsed = [int(run["elapsed_ms"]) for run in completed if run.get("elapsed_ms") is not None]
    costs = [
        float((run.get("metadata") or {}).get("costs") or 0)
        for run in runs
        if isinstance((run.get("metadata") or {}).get("costs"), (int, float))
    ]
    sources = [
        int((run.get("metadata") or {}).get("sources") or 0)
        for run in runs
        if isinstance((run.get("metadata") or {}).get("sources"), (int, float))
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
        "latency_p50_ms": _percentile(elapsed, 0.50),
        "latency_p95_ms": _percentile(elapsed, 0.95),
        "mean_report_chars": round(statistics.mean([r["report_chars"] for r in completed]), 1)
        if completed
        else None,
        "total_costs": round(sum(costs), 6) if costs else None,
        "total_sources": sum(sources),
        "audit_totals": audit_totals,
        "error_types": sorted({run.get("error_type") for run in failed if run.get("error_type")}),
    }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "web",
        "retriever": settings.gptr_retriever,
        "backend": settings.research_backend,
        "models": {
            "fast": settings.gptr_fast_llm,
            "smart": settings.gptr_smart_llm,
            "strategic": settings.gptr_strategic_llm,
        },
        "allow_private_urls": bool(args.allow_private),
        "note": (
            "当前代理环境使用 ALLOW_PRIVATE_URLS=true 放行 198.18.x；"
            "外部链接未做内容核验，不能把本结果写成生产稳定性。"
        ),
        "summary": summary,
        "tasks": runs,
    }
    _write_output(payload)
    (ROOT / "docs" / "web_research_runs.md").write_text(_markdown(payload), encoding="utf-8")
    print("\n# Web research evaluation")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if failed == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
