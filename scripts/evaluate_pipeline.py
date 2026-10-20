"""Reproducible pipeline evaluation on the *synthetic* fixture papers.

This script is deliberately honest about its corpus: three PDFs are generated
from fixed fixtures (two prose papers and one ruled table), the embedding
backend is the lexical hash embedder, and the numbers below measure plumbing
(field recall, retrieval rank, citation acceptance, latency) — not scientific
quality on real papers.

Usage:
    python scripts/evaluate_pipeline.py
Writes docs/evaluation_results.json and prints a Markdown summary.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The application reads WORKSPACE_DIR at import time. Point it at the isolated
# test workspace *before* importing the app, otherwise cleanup would touch the
# developer's real workspace/ directory.
os.environ.setdefault("WORKSPACE_DIR", str(ROOT / ".test-workspace"))

# Importing the test harness also sets fixture env vars and imports the app.
from fastapi.testclient import TestClient  # noqa: E402

from spectrascholar.main import app  # noqa: E402
from tests.conftest import (  # noqa: E402
    DYNAMIC_GNN_PAGES,
    HYBRIDSN_PAGES,
    _clean_workspace,
    make_pdf_bytes,
    make_table_pdf_bytes,
)

EXPECTED = {
    "dynamic_gnn.pdf": {
        "title_prefix": "Dynamic Graph Neural Networks",
        "methods": {"GCN"},
        "datasets": {"Indian Pines"},
        "metrics": {("OA", "98.4%"), ("Kappa", "0.977")},
        "graphs": {"KNN", "dynamic"},
        "train_ratio": "10%",
        "patch_size": "9x9",
    },
    "hybridsn.pdf": {
        "title_prefix": "HybridSN",
        "methods": {"HybridSN"},
        "datasets": {"Indian Pines"},
        "metrics": {("OA", "97.1%"), ("AA", "96.5%")},
        "graphs": {"RBF", "static"},
        "train_ratio": "10%",
        "patch_size": "9x9",
    },
    "table_paper.pdf": {
        "title_prefix": None,
        "methods": {"HybridSN", "GCN"},
        "datasets": {"Indian Pines"},
        "metrics": {
            ("OA", "98.4"),
            ("AA", "97.8"),
            ("Kappa", "0.976"),
            ("OA", "97.1"),
            ("AA", "96.5"),
            ("Kappa", "0.965"),
        },
        "graphs": set(),
        "train_ratio": "10%",
        "patch_size": "9x9",
    },
}

RAG_LABELS = [
    {"query": "dynamic graph KNN graph construction", "filename": "dynamic_gnn.pdf", "page": 1},
    {"query": "HybridSN 3D-CNN 2D-CNN spectral-spatial", "filename": "hybridsn.pdf", "page": 1},
    {"query": "overall accuracy 98.4 Indian Pines training samples", "filename": "dynamic_gnn.pdf", "page": 2},
    {"query": "static graph RBF baseline", "filename": "hybridsn.pdf", "page": 2},
]


def _upload(client: TestClient, name: str, pages: list[list[str]]) -> str:
    response = client.post(
        "/api/v1/documents",
        files={"file": (name, make_pdf_bytes(pages), "application/pdf")},
    )
    response.raise_for_status()
    return response.json()["document_id"]


def _upload_table(client: TestClient, name: str) -> str:
    response = client.post(
        "/api/v1/documents",
        files={"file": (name, make_table_pdf_bytes(), "application/pdf")},
    )
    response.raise_for_status()
    return response.json()["document_id"]


def _run_retrieval_mode(client: TestClient, labels: list[dict], mode: str) -> list[dict]:
    runs = []
    for label in labels:
        started = time.perf_counter()
        response = client.post(
            "/api/v1/kb/search",
            json={"query": label["query"], "top_k": 5, "mode": mode},
        )
        response.raise_for_status()
        latency_ms = int((time.perf_counter() - started) * 1000)
        hits = response.json()["hits"]
        ranks = [
            rank
            for rank, hit in enumerate(hits, 1)
            if hit["filename"] == label["filename"] and hit["page"] == label["page"]
        ]
        runs.append(
            {
                **label,
                "mode": mode,
                "rank": ranks[0] if ranks else None,
                "latency_ms": latency_ms,
                "top_hit": hits[0]["filename"] + f" p.{hits[0]['page']}" if hits else None,
            }
        )
    return runs


def _retrieval_metrics(runs: list[dict]) -> dict:
    ranks = [run["rank"] for run in runs]
    return {
        "queries": len(ranks),
        "recall_at_1": round(sum(1 for rank in ranks if rank == 1) / len(ranks), 4) if ranks else None,
        "recall_at_3": round(sum(1 for rank in ranks if rank and rank <= 3) / len(ranks), 4)
        if ranks
        else None,
        "mrr": round(sum((1 / rank) for rank in ranks if rank) / len(ranks), 4) if ranks else None,
        "median_latency_ms": int(statistics.median(run["latency_ms"] for run in runs)) if runs else None,
        "runs": runs,
    }


def _extraction_metrics(papers: list[dict]) -> dict:
    per_paper = []
    total_fields = hit_fields = 0
    evidence_total = evidence_verified = 0
    for paper in papers:
        filename = paper["filename"]
        expected = EXPECTED[filename]
        methods = {method["name"] for method in paper["methods"]}
        datasets = {dataset["name"] for dataset in paper["datasets"]}
        metrics = {(metric["metric"], metric["value"]) for metric in paper["metrics"]}
        graphs = {graph["kind"] for graph in paper["graph_constructions"]}
        checks = {
            "methods": expected["methods"] <= methods,
            "datasets": expected["datasets"] <= datasets,
            "metrics": expected["metrics"] <= metrics,
            "graph": expected["graphs"] <= graphs,
            "train_ratio": any(metric.get("train_ratio") == expected["train_ratio"] for metric in paper["metrics"]),
            "patch_size": any(metric.get("patch_size") == expected["patch_size"] for metric in paper["metrics"]),
        }
        if expected.get("title_prefix"):
            checks["title"] = bool(paper["metadata"]["title"]["value"]) and paper["metadata"]["title"][
                "value"
            ].startswith(expected["title_prefix"])
        evidence = []
        for method in paper["methods"]:
            evidence.extend(method["evidence"])
        for dataset in paper["datasets"]:
            evidence.extend(dataset["evidence"])
        for graph in paper["graph_constructions"]:
            evidence.extend(graph["evidence"])
        for metric in paper["metrics"]:
            evidence.extend(metric["evidence"])
        evidence_total += len(evidence)
        evidence_verified += sum(1 for item in evidence if item["status"] == "verified_quote")
        total_fields += len(checks)
        hit_fields += sum(checks.values())
        per_paper.append({"filename": filename, "checks": checks})
    return {
        "field_accuracy": round(hit_fields / total_fields, 4) if total_fields else None,
        "fields_passed": hit_fields,
        "fields_total": total_fields,
        "evidence_acceptance": round(evidence_verified / evidence_total, 4) if evidence_total else None,
        "evidence_verified": evidence_verified,
        "evidence_total": evidence_total,
        "per_paper": per_paper,
    }


def main() -> None:
    _clean_workspace()
    with TestClient(app) as client:
        ids = {
            "dynamic_gnn.pdf": _upload(client, "dynamic_gnn.pdf", DYNAMIC_GNN_PAGES),
            "hybridsn.pdf": _upload(client, "hybridsn.pdf", HYBRIDSN_PAGES),
            "table_paper.pdf": _upload_table(client, "table_paper.pdf"),
        }

        started = time.perf_counter()
        comparison = client.post(
            "/api/v1/compare",
            json={"document_ids": list(ids.values()), "mode": "heuristic"},
        )
        comparison.raise_for_status()
        comparison_json = comparison.json()
        compare_latency_ms = int((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        index = client.post("/api/v1/kb/index", json={})
        index.raise_for_status()
        index_latency_ms = int((time.perf_counter() - started) * 1000)

        retrieval_modes = {
            mode: _run_retrieval_mode(client, RAG_LABELS, mode) for mode in ("bm25", "vector", "hybrid")
        }

        started = time.perf_counter()
        answer = client.post(
            "/api/v1/kb/answer",
            json={"query": "What accuracy does the dynamic graph method report on Indian Pines?", "top_k": 5},
        )
        answer.raise_for_status()
        answer_json = answer.json()
        answer_latency_ms = int((time.perf_counter() - started) * 1000)

        started = time.perf_counter()
        workflow = client.post(
            "/api/v1/workflows",
            json={
                "topic": "比较动态图 GNN 与 HybridSN 的实验条件",
                "document_ids": list(ids.values()),
                "extraction_mode": "heuristic",
                "idempotency_key": "evaluation-fixture",
            },
        )
        workflow.raise_for_status()
        workflow_id = workflow.json()["workflow_id"]
        for _ in range(300):
            workflow_json = client.get(f"/api/v1/workflows/{workflow_id}").json()
            if workflow_json["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)
        workflow_latency_ms = int((time.perf_counter() - started) * 1000)

    retrieval_metrics = {
        mode: _retrieval_metrics(runs) for mode, runs in retrieval_modes.items()
    }
    hybrid_metrics = retrieval_metrics["hybrid"]
    extraction = _extraction_metrics(comparison_json["papers"])
    citation_checks = answer_json["citations"]
    citation_failed = sum(
        1
        for check in citation_checks
        if check["status"] not in {"verified_quote", "verified_page_only"}
    )
    results = {
        "corpus": "synthetic_fixture",
        "real_papers": False,
        "embedding_backend": index.json()["embedding_backend"],
        "note": (
            "合成两页论文夹具，仅验证抽取/检索/引用流水线；"
            "不代表真实论文上的科学正确率或语义检索质量。"
        ),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "documents": len(ids),
        "chunks": index.json()["total_chunks"],
        "extraction": extraction,
        "retrieval": {
            "primary_mode": "hybrid",
            "queries": hybrid_metrics["queries"],
            "recall_at_1": hybrid_metrics["recall_at_1"],
            "recall_at_3": hybrid_metrics["recall_at_3"],
            "mrr": hybrid_metrics["mrr"],
            "modes": {
                mode: {key: value for key, value in metrics.items() if key != "runs"}
                for mode, metrics in retrieval_metrics.items()
            },
            "runs": hybrid_metrics["runs"],
        },
        "citation": {
            "answer_mode": answer_json["answer_mode"],
            "grounded": answer_json["grounded"],
            "total_checks": len(citation_checks),
            "failed_checks": citation_failed,
            "validity": round((len(citation_checks) - citation_failed) / len(citation_checks), 4)
            if citation_checks
            else None,
        },
        "workflow": {
            "status": workflow_json["status"],
            "steps_completed": sum(1 for step in workflow_json["steps"] if step["status"] == "completed"),
            "steps_total": len(workflow_json["steps"]),
            "elapsed_ms": workflow_json.get("elapsed_ms"),
        },
        "latency_ms": {
            "compare": compare_latency_ms,
            "index": index_latency_ms,
            "search_median": hybrid_metrics["median_latency_ms"],
            "answer": answer_latency_ms,
            "workflow": workflow_latency_ms,
        },
    }
    output = ROOT / "docs" / "evaluation_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("# Fixture evaluation (synthetic papers)")
    print()
    print(f"- Corpus: {results['corpus']} / real_papers={results['real_papers']}")
    print(f"- Embedding: {results['embedding_backend']}")
    print(f"- Extraction field accuracy: {extraction['fields_passed']}/{extraction['fields_total']} "
          f"({extraction['field_accuracy']})")
    print(f"- Evidence acceptance: {extraction['evidence_verified']}/{extraction['evidence_total']} "
          f"({extraction['evidence_acceptance']})")
    for mode, metrics in retrieval_metrics.items():
        print(
            f"- Retrieval [{mode}]: Recall@1={metrics['recall_at_1']} "
            f"Recall@3={metrics['recall_at_3']} MRR={metrics['mrr']} "
            f"median={metrics['median_latency_ms']}ms"
        )
    print(f"- Citation validity: {results['citation']['validity']} "
          f"({results['citation']['total_checks']} checks)")
    print(f"- Workflow: {results['workflow']['status']} "
          f"{results['workflow']['steps_completed']}/{results['workflow']['steps_total']} steps")
    print(f"- Latency: {results['latency_ms']}")
    print(f"- Written: {output}")


if __name__ == "__main__":
    main()
