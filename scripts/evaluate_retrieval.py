"""Evaluate real-paper retrieval on 30 manually labeled questions.

Modes are deliberately simple and inspectable:
* BM25 over page chunks;
* embedding-vector cosine over the same chunks;
* hybrid RRF of both rankings.

Gold is a document/page.  This measures retrieval/page hit, not answer quality.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if "--ocr" in sys.argv:
    os.environ["OCR_ENABLED"] = "1"
EMBEDDING_BACKEND = "hash"
if "--embedding" in sys.argv:
    position = sys.argv.index("--embedding")
    if position + 1 < len(sys.argv):
        EMBEDDING_BACKEND = sys.argv[position + 1].lower()
for argument in sys.argv:
    if argument.startswith("--embedding="):
        EMBEDDING_BACKEND = argument.split("=", 1)[1].lower()
os.environ["EMBEDDING_BACKEND"] = EMBEDDING_BACKEND

from spectrascholar.evidence import read_pdf_pages  # noqa: E402
from spectrascholar.extraction.ocr import augment_pages_with_ocr  # noqa: E402
from spectrascholar.rag.bm25 import BM25, tokenize  # noqa: E402
from spectrascholar.rag.chunking import chunk_page  # noqa: E402
from spectrascholar.rag.embeddings import EmbeddingError, HashEmbedder, get_embedder  # noqa: E402
from spectrascholar.rag.table_meta import table_boost  # noqa: E402
from spectrascholar.settings import settings  # noqa: E402

PAPER_FILES = {
    "hybridsn": "HybridSN Exploring 3-D–2-D CNN Feature Hierarchy for Hyperspectral Image Classification.pdf",
    "ssrn": "spectral-spatial_residual_networks_for_hyperspectral_image_classification_a_3d_deep_learning_framework_0.pdf",
    "cnn_gat": "Weighted_Feature_Fusion_of_Convolutional_Neural_Network_and_Graph_Attention_Network_for_Hyperspectral_Image_Classification.pdf",
}
MODES = ("bm25", "hash", "vector", "hybrid", "router")
METADATA_RE = re.compile(r"年份|发表|期刊|会议|作者|主方法|标题|DOI|venue|year|author", re.I)
METRIC_RE = re.compile(r"\bOA\b|\bAA\b|Kappa|accuracy|准确率|精度|指标|训练比例|patch|补丁", re.I)


def _route_question(query: str) -> str:
    """Small deterministic router; the eval and product share this policy."""
    if METADATA_RE.search(query):
        return "hash"
    if METRIC_RE.search(query):
        return "vector"
    return "hybrid"


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
    hash_vectors: list[list[float]],
    vectors: list[list[float]],
    embedder,
    page_texts: dict[tuple[str, int], str],
    limit: int = 20,
) -> list[int]:
    if mode == "router":
        return _rank(
            _route_question(query),
            query,
            chunks,
            bm25,
            hash_vectors,
            vectors,
            embedder,
            page_texts,
            limit,
        )
    if mode == "bm25":
        ranked = [index for index, _ in bm25.top_k(query, limit)]
        return _table_rerank(ranked, query, chunks, page_texts)
    if mode == "hash":
        hash_query = asyncio.run(HashEmbedder().embed([query]))[0]
        hash_scores = [_cosine(hash_query, vector) for vector in hash_vectors]
        ranked = sorted(
            range(len(chunks)), key=lambda index: hash_scores[index], reverse=True
        )[:limit]
        return _table_rerank(ranked, query, chunks, page_texts)
    query_vector = asyncio.run(embedder.embed([query]))[0]
    vector_scores = [_cosine(query_vector, vector) for vector in vectors]
    if mode == "vector":
        ranked = sorted(
            range(len(chunks)), key=lambda index: vector_scores[index], reverse=True
        )[:limit]
        return _table_rerank(ranked, query, chunks, page_texts)
    bm25_rank = [index for index, _ in bm25.top_k(query, limit)]
    vector_rank = sorted(
        range(len(chunks)), key=lambda index: vector_scores[index], reverse=True
    )[:limit]
    fused: dict[int, float] = defaultdict(float)
    for rank, index in enumerate(bm25_rank, 1):
        fused[index] += 1.0 / (60 + rank)
    for rank, index in enumerate(vector_rank, 1):
        fused[index] += 1.0 / (60 + rank)
    ranked = [index for index, _ in sorted(fused.items(), key=lambda item: item[1], reverse=True)]
    return _table_rerank(ranked, query, chunks, page_texts)


def _table_rerank(
    ranked: list[int],
    query: str,
    chunks: list,
    page_texts: dict[tuple[str, int], str],
) -> list[int]:
    rescored = []
    for rank, index in enumerate(ranked, 1):
        chunk = chunks[index]
        boost = table_boost(query, page_texts.get((chunk.document_id, chunk.page), ""))
        rescored.append((index, 1.0 / (20 + rank) + 0.30 * boost))
    rescored.sort(key=lambda item: item[1], reverse=True)
    return [index for index, _ in rescored]


def _load_chunks() -> tuple[list, dict[str, int]]:
    chunks = []
    page_counts: dict[str, int] = {}
    for paper_id, filename in PAPER_FILES.items():
        path = ROOT / "workspace" / "papers" / filename
        pages = read_pdf_pages(path)
        if settings.ocr_enabled:
            pages, _ = augment_pages_with_ocr(pages, path)
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


def _normalized_text(text: str) -> str:
    normalized = text.casefold().replace("×", "x").replace("–", "-")
    normalized = re.sub(r"\s*([x%])\s*", r"\1", normalized)
    return " ".join(normalized.split())


def _answer_tokens(item: dict) -> list[str]:
    answer = _normalized_text(item["gold_answer"])
    if item["category"] == "condition":
        tokens = re.findall(r"\d+(?:\.\d+)?%|\d+x\d+", answer)
        return tokens or [answer]
    return [answer]


def _answer_hit(chunk, item: dict) -> bool:
    if chunk.document_id != item["document_id"]:
        return False
    if chunk.page == item["gold_page"]:
        return True
    text = _normalized_text(chunk.text)
    return all(token in text for token in _answer_tokens(item))


def _score(rows: list[dict], mode: str, k: int, *, page_only: bool = False) -> dict:
    hits = 0
    reciprocal = 0.0
    field = "page_ranks" if page_only else "ranks"
    for row in rows:
        rank = row[field][mode]
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
    hash_vectors = asyncio.run(HashEmbedder().embed([chunk.text for chunk in chunks]))
    embedder = get_embedder(EMBEDDING_BACKEND)
    try:
        vectors = asyncio.run(embedder.embed([chunk.text for chunk in chunks]))
    except EmbeddingError as exc:
        print(f"REAL_EMBEDDING_BLOCKED: {exc.code}: {exc}")
        raise SystemExit(2) from exc
    page_chunks: dict[tuple[str, int], list[str]] = defaultdict(list)
    for chunk in chunks:
        page_chunks[(chunk.document_id, chunk.page)].append(chunk.text)
    page_texts = {key: "\n".join(parts) for key, parts in page_chunks.items()}
    rows = []
    for item in payload["items"]:
        ranks = {}
        page_ranks = {}
        for mode in MODES:
            ranked = _rank(
                mode,
                item["question"],
                chunks,
                bm25,
                hash_vectors,
                vectors,
                embedder,
                page_texts,
            )
            first = None
            page_first = None
            for rank, index in enumerate(ranked, 1):
                chunk = chunks[index]
                if chunk.document_id != item["document_id"]:
                    continue
                if page_first is None and chunk.page == item["gold_page"]:
                    page_first = rank
                if first is None and _answer_hit(chunk, item):
                    first = rank
                if first is not None and page_first is not None:
                    break
            ranks[mode] = first
            page_ranks[mode] = page_first
        rows.append({**item, "ranks": ranks, "page_ranks": page_ranks})
    summary = {mode: {f"k={k}": _score(rows, mode, k) for k in (1, 3, 5)} for mode in MODES}
    page_summary = {
        mode: {f"k={k}": _score(rows, mode, k, page_only=True) for k in (1, 3, 5)}
        for mode in MODES
    }
    by_category: dict[str, dict] = {}
    for category in sorted({row["category"] for row in rows}):
        subset = [row for row in rows if row["category"] == category]
        by_category[category] = {mode: _score(subset, mode, 5) for mode in MODES}
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": payload["corpus"],
        "questions": len(rows),
        "chunks": len(chunks),
        "embedding_backend": embedder.name,
        "page_counts": page_counts,
        "summary": summary,
        "page_summary": page_summary,
        "by_category": by_category,
        "items": rows,
        "note": "Answer hit = same document and (gold page or gold answer string in chunk); page hit is stricter. Table-page metadata rerank is applied. Vector mode uses the configured embedding backend; hash is a separate baseline.",
    }


def write_markdown(result: dict) -> str:
    lines = [
        "# 真实论文检索评测",
        "",
        f"- 生成时间：{result['generated_at']}",
        f"- 问题数：{result['questions']}",
        f"- chunk 数：{result['chunks']}",
        "- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。",
        "- Page hit：必须命中人工标注的 gold page；更严格。",
        f"- `vector` 使用 {result.get('embedding_backend', 'configured')}；hash 是另一条词法基线。",
        "",
        "## Answer-level 总览",
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
    lines += ["", "## 严格 Page-level 总览", "", "| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |", "|---|---:|---:|---:|---:|"]
    for mode in MODES:
        summary = result["page_summary"][mode]
        lines.append(
            f"| {mode} | {summary['k=1']['recall@1']:.2%} | "
            f"{summary['k=3']['recall@3']:.2%} | {summary['k=5']['recall@5']:.2%} | "
            f"{summary['k=5']['mrr@5']:.4f} |"
        )
    lines += ["", "## 分类（answer-level）", "", "| 类别 | 模式 | Recall@5 | MRR@5 |", "|---|---|---:|---:|"]
    for category, modes in result["by_category"].items():
        for mode, score in modes.items():
            lines.append(
                f"| {category} | {mode} | {score['recall@5']:.2%} | {score['mrr@5']:.4f} |"
            )
    lines += ["", "## 未命中示例（hybrid answer-level，前 10 条）", ""]
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
