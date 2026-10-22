"""Evaluate real-paper retrieval on 30 manually labeled questions.

Modes are deliberately simple and inspectable:
* BM25 over page chunks;
* hash-vector cosine over the same chunks;
* hybrid RRF of both rankings.

Gold is a document/page.  This measures retrieval/page hit, not answer quality.
"""
from __future__ import annotations

import asyncio
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from spectrascholar.evidence import read_pdf_pages  # noqa: E402
from spectrascholar.rag.bm25 import BM25, tokenize  # noqa: E402
from spectrascholar.rag.chunking import chunk_page  # noqa: E402
from spectrascholar.rag.embeddings import HashEmbedder  # noqa: E402

PAPER_FILES = {
    "hybridsn": "HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf",
    "ssrn": "spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf",
    "wfcg": "Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf",
}
MODES = ("bm25", "hash", "hybrid")


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def _rank(
    mode: str,
    query: str,
    chunks: list,
    bm25: BM25,
    vectors: list[list[float]],
    embedder: HashEmbedder,
    limit: int = 20,
) -> list[int]:
    if mode == "bm25":
        return [index for index, _ in bm25.top_k(query, limit)]
    query_vector = asyncio.run(embedder.embed([query]))[0]
    vector_scores = [_cosine(query_vector, vector) for vector in vectors]
    if mode == "hash":
        return sorted(range(len(chunks)), key=lambda index: vector_scores[index], reverse=True)[:limit]
    bm25_rank = [index for index, _ in bm25.top_k(query, limit)]
    hash_rank = sorted(range(len(chunks)), key=lambda index: vector_scores[index], reverse=True)[:limit]
    fused: dict[int, float] = defaultdict(float)
    for rank, index in enumerate(bm25_rank, 1):
        fused[index] += 1.0 / (60 + rank)
    for rank, index in enumerate(hash_rank, 1):
        fused[index] += 1.0 / (60 + rank)
    return [index for index, _ in sorted(fused.items(), key=lambda item: item[1], reverse=True)[:limit]]


def _load_chunks() -> tuple[list, dict[str, int]]:
    chunks = []
    page_counts: dict[str, int] = {}
    for paper_id, filename in PAPER_FILES.items():
        pages = read_pdf_pages(ROOT / "workspace" / "papers" / filename)
        page_counts[paper_id] = len(pages)
        for page_number, text in enumerate(pages, 1):
            chunks.extend(
                chunk_page(
                    paper_id,
                    page_number,
                    text,
                    max_chars=900,
                    overlap=120,
                )
            )
    return chunks, page_counts


def _score(rows: list[dict], mode: str, k: int) -> dict:
    hits = 0
    reciprocal = 0.0
    for row in rows:
        rank = row["ranks"][mode]
        if rank and rank <= k:
            hits += 1
            reciprocal += 1.0 / rank
    total = len(rows)
    return {
        f"recall@{k}": round(hits / total, 4) if total else 0.0,
        f"mrr@{k}": round(reciprocal / total, 4) if total else 0.0,
        "hits": hits,
        "total": total,
    }


def run() -> dict:
    payload = json.loads((ROOT / "eval" / "research_eval.json").read_text(encoding="utf-8"))
    chunks, page_counts = _load_chunks()
    bm25 = BM25([tokenize(chunk.text) for chunk in chunks])
    embedder = HashEmbedder()
    vectors = asyncio.run(embedder.embed([chunk.text for chunk in chunks]))
    rows = []
    for item in payload["items"]:
        ranks = {}
        for mode in MODES:
            ranked = _rank(mode, item["question"], chunks, bm25, vectors, embedder)
            first = None
            for rank, index in enumerate(ranked, 1):
                chunk = chunks[index]
                if chunk.document_id == item["document_id"] and chunk.page == item["gold_page"]:
                    first = rank
                    break
            ranks[mode] = first
        rows.append({**item, "ranks": ranks})
    summary = {mode: {f"k={k}": _score(rows, mode, k) for k in (1, 3, 5)} for mode in MODES}
    by_category: dict[str, dict] = {}
    for category in sorted({row["category"] for row in rows}):
        subset = [row for row in rows if row["category"] == category]
        by_category[category] = {mode: _score(subset, mode, 5) for mode in MODES}
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": payload["corpus"],
        "questions": len(rows),
        "chunks": len(chunks),
        "page_counts": page_counts,
        "summary": summary,
        "by_category": by_category,
        "items": rows,
        "note": "Gold is document/page from manual labels. Hash vectors are lexical hashing, not semantic embeddings.",
    }


def write_markdown(result: dict) -> str:
    lines = [
        "# 真实论文检索评测",
        "",
        f"- 生成时间：{result['generated_at']}",
        f"- 问题数：{result['questions']}",
        f"- chunk 数：{result['chunks']}",
        "- Gold：人工标注的 document/page；只评检索/页码命中，不评回答语义。",
        "- `hash` 是词法哈希，不是语义 embedding。",
        "",
        "## 总览",
        "",
        "| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |",
        "|---|---:|---:|---:|---:|",
    ]
    for mode in MODES:
        summary = result["summary"][mode]
        lines.append(
            f"| {mode} | {summary['k=1']['recall@1']:.2%} | "
            f"{summary['k=3']['recall@3']:.2%} | {summary['k=5']['recall@5']:.2%} | "
            f"{summary['k=5']['mrr@5']:.4f} |"
        )
    lines += ["", "## 分类", "", "| 类别 | 模式 | Recall@5 | MRR@5 |", "|---|---|---:|---:|"]
    for category, modes in result["by_category"].items():
        for mode, score in modes.items():
            lines.append(
                f"| {category} | {mode} | {score['recall@5']:.2%} | {score['mrr@5']:.4f} |"
            )
    lines += ["", "## 未命中示例（hybrid，前 10 条）", ""]
    misses = [row for row in result["items"] if not row["ranks"]["hybrid"]]
    if not misses:
        lines.append("无未命中。")
    else:
        for row in misses[:10]:
            lines.append(f"- `{row['id']}` {row['question']}（gold p.{row['gold_page']}）")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    result = run()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "retrieval_runs.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (docs / "retrieval_runs.md").write_text(write_markdown(result) + "\n", encoding="utf-8")
    for mode in MODES:
        summary = result["summary"][mode]
        print(
            f"{mode}: Recall@1={summary['k=1']['recall@1']:.2%} "
            f"Recall@3={summary['k=3']['recall@3']:.2%} "
            f"Recall@5={summary['k=5']['recall@5']:.2%} "
            f"MRR@5={summary['k=5']['mrr@5']:.4f}"
        )
    print("written: docs/retrieval_runs.md/json")


if __name__ == "__main__":
    main()
