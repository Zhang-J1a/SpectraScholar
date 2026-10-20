"""Summarize a saved comparison JSON without over-claiming semantic accuracy.

Usage:
    python scripts/evaluate_evidence.py comparison.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(path: Path) -> int:
    result = json.loads(path.read_text(encoding="utf-8"))
    papers = result.get("papers", [])
    evidence = []
    for paper in papers:
        for method in paper.get("methods", []):
            evidence.extend(method.get("evidence", []))
        for dataset in paper.get("datasets", []):
            evidence.extend(dataset.get("evidence", []))
        for graph in paper.get("graph_constructions", []):
            evidence.extend(graph.get("evidence", []))
        for metric in paper.get("metrics", []):
            evidence.extend(metric.get("evidence", []))
    verified = sum(1 for item in evidence if item.get("status") == "verified_quote")
    comparable = sum(1 for row in result.get("metric_rows", []) if row.get("comparable"))
    metrics = len(result.get("metric_rows", []))
    print(f"PDF 原文证据通过: {verified}/{len(evidence)}")
    print(f"可比较指标: {comparable}/{metrics}（仅条件完全一致时才可排名）")
    print("注意：本指标不衡量模型召回率、语义正确性、检索质量或科学结论正确性。")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("comparison", type=Path)
    raise SystemExit(main(parser.parse_args().comparison))
