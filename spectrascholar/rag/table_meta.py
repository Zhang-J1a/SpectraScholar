"""Table-page metadata and query-aware reranking.

This is intentionally deterministic: it detects table captions, datasets,
metric rows, training ratios and patch sizes from page text.  It does not call
an LLM and does not claim semantic relevance.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DATASET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Indian Pines", re.compile(r"\b(?:INDIAN\s+PIN(?:E)?S?|IN\s+DATA\s+SET)\b", re.I)),
    ("Pavia University", re.compile(r"\b(?:UNIVERSITY\s+OF\s+PAV(?:IA)?|UP\s+DATA\s+SET)\b", re.I)),
    ("Kennedy Space Center", re.compile(r"\b(?:KSC|KENNEDY\s+SPACE\s+CENTER)\b", re.I)),
    ("Salinas", re.compile(r"\bSALINAS\b", re.I)),
    ("WHU-Hi", re.compile(r"\bWHU[-\s]?HI\b", re.I)),
)
METRIC_RE = re.compile(r"\b(OA|AA|KAPPA)\b|KAPPA\s*[X×]\s*100", re.I)
RATIO_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
PATCH_RE = re.compile(r"\b\d{1,3}\s*[x×]\s*\d{1,3}\b", re.I)
METHOD_RE = re.compile(r"\b(?:SVM|SAE|CNN|CNNL|SPA|SPC|SSRN|WFCG|WECG|GCN|GAT|JSAN|JSSAN|HYBRIDSN|HYBIRDSN)\b", re.I)
TABLE_LINE_RE = re.compile(r"\bTABLE\s+[IVXLC\d]+", re.I)


@dataclass
class TableMeta:
    has_table: bool = False
    caption: str = ""
    datasets: set[str] = field(default_factory=set)
    metrics: set[str] = field(default_factory=set)
    ratios: set[str] = field(default_factory=set)
    patches: set[str] = field(default_factory=set)
    methods: set[str] = field(default_factory=set)


def _normalize_ratio(value: str) -> str:
    return value.replace(" ", "").casefold()


def _normalize_patch(value: str) -> str:
    return re.sub(r"\s*[x×]\s*", "x", value.casefold())


def table_meta(text: str) -> TableMeta:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    caption_lines = [
        line
        for line in lines
        if TABLE_LINE_RE.search(line) or "DATA SET" in line.upper() or "DATASET" in line.upper()
    ]
    caption = " ".join(caption_lines[:3])[:300]
    datasets = {name for name, pattern in DATASET_PATTERNS if pattern.search(text)}
    metrics: set[str] = set()
    for match in METRIC_RE.finditer(text):
        if match.group(1):
            metrics.add(match.group(1).upper())
        elif "KAPPA" in match.group(0).upper():
            metrics.add("Kappa")
    ratios = {_normalize_ratio(match.group(0)) for match in RATIO_RE.finditer(text)}
    patches = {_normalize_patch(match.group(0)) for match in PATCH_RE.finditer(text)}
    methods = {match.group(0).upper() for match in METHOD_RE.finditer(text)}
    has_table = bool(caption_lines and (metrics or ratios or patches))
    return TableMeta(
        has_table=has_table,
        caption=caption,
        datasets=datasets,
        metrics=metrics,
        ratios=ratios,
        patches=patches,
        methods=methods,
    )


def query_signals(query: str) -> TableMeta:
    """Extract table-related signals from a user question."""
    metrics: set[str] = set()
    for match in METRIC_RE.finditer(query):
        if match.group(1):
            metrics.add(match.group(1).upper())
        elif "KAPPA" in match.group(0).upper():
            metrics.add("Kappa")
    ratios = {_normalize_ratio(match.group(0)) for match in RATIO_RE.finditer(query)}
    patches = {_normalize_patch(match.group(0)) for match in PATCH_RE.finditer(query)}
    datasets = {name for name, pattern in DATASET_PATTERNS if pattern.search(query)}
    methods = {match.group(0).upper() for match in METHOD_RE.finditer(query)}
    table_intent = bool(
        metrics
        or ratios
        or patches
        or re.search(r"(指标|准确率|训练比例|patch|table|table\s+\d+)", query, re.I)
    )
    return TableMeta(
        has_table=table_intent,
        datasets=datasets,
        metrics=metrics,
        ratios=ratios,
        patches=patches,
        methods=methods,
    )


def table_boost(query: str, page_text: str) -> float:
    """Small deterministic boost for pages that contain the requested table fields."""
    wanted = query_signals(query)
    if not wanted.has_table:
        return 0.0
    found = table_meta(page_text)
    boost = 0.0
    if found.has_table:
        boost += 0.20
    if wanted.datasets and wanted.datasets & found.datasets:
        boost += 0.20
    if wanted.metrics and wanted.metrics & found.metrics:
        boost += 0.10
    if wanted.ratios and wanted.ratios & found.ratios:
        boost += 0.10
    if wanted.patches and wanted.patches & found.patches:
        boost += 0.10
    if wanted.methods and wanted.methods & found.methods:
        boost += 0.05
    return min(boost, 0.55)
