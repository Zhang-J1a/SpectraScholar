"""Deterministic query router for the local retrieval index."""
from __future__ import annotations

import re

METADATA_RE = re.compile(r"年份|发表|期刊|会议|作者|主方法|标题|DOI|venue|year|author", re.I)
METRIC_RE = re.compile(r"\bOA\b|\bAA\b|Kappa|accuracy|准确率|精度|指标|训练比例|patch|补丁", re.I)


def route_question(query: str) -> str:
    """Choose a product retrieval mode.

    Metadata questions favour BM25; metric/condition questions favour the
    configured embedding vector; everything else uses hybrid RRF.
    """
    if METADATA_RE.search(query):
        return "bm25"
    if METRIC_RE.search(query):
        return "vector"
    return "hybrid"
