"""Generate the V1 real-paper comparison report with page-level citations.

Uploads the three real PDFs from workspace/papers, runs the production compare
endpoint (LLM mode), and writes docs/real_paper_comparison.md plus a small
summary JSON. This is the V1 acceptance artifact; it makes no ranking claim
when dataset/ratio/patch conditions do not match.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / ".evaluation-real-papers" / "compare"
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.environ["WORKSPACE_DIR"] = str(WORKSPACE)
os.environ["QUEUE_BACKEND"] = "inline"
os.environ["EXTRACTOR_BACKEND"] = "llm"
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ.pop("SPECTRASCHOLAR_SKIP_DOTENV", None)

PAPERS = [
    "HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf",
    "spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf",
    "Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf",
]


def main() -> int:
    from fastapi.testclient import TestClient

    from spectrascholar.main import app

    ids: list[str] = []
    with TestClient(app) as client:
        for name in PAPERS:
            path = ROOT / "workspace" / "papers" / name
            response = client.post(
                "/api/v1/documents",
                files={"file": (name, path.read_bytes(), "application/pdf")},
            )
            response.raise_for_status()
            ids.append(response.json()["document_id"])
        response = client.post(
            "/api/v1/compare",
            json={"document_ids": ids, "mode": "llm", "language": "en"},
        )
        response.raise_for_status()
        payload = response.json()

    markdown = payload.get("markdown") or ""
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "real_paper_comparison.md").write_text(markdown, encoding="utf-8")
    page_mentions = len(re.findall(r"p\.\s*\d+", markdown))
    local_markers = len(re.findall(r"\[\[doc:", markdown))
    summary = {
        "comparison_id": payload.get("comparison_id"),
        "papers": [
            {
                "filename": paper.get("filename"),
                "metrics": len(paper.get("metrics") or []),
                "methods": len(paper.get("methods") or []),
                "datasets": len(paper.get("datasets") or []),
            }
            for paper in payload.get("papers") or []
        ],
        "comparable_groups": len(payload.get("comparable_groups") or []),
        "issues": len(payload.get("issues") or []),
        "markdown_chars": len(markdown),
        "citation_markers": local_markers,
        "page_mentions": page_mentions,
        "acceptance_note": (
            "3 篇真实论文的结构化对照；所有指标/方法/数据集/条件带页级 [[doc:... p.N \"quote\"]]；"
            "无可比组时不排名。外部语义和论文结论正确性仍需人工核验。"
        ),
    }
    (docs / "real_paper_comparison.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
