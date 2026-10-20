"""Extraction service: choose an extractor and load the PDF exactly once."""
from __future__ import annotations

from pathlib import Path

from ..evidence import read_pdf_pages
from ..schemas import PaperExtraction
from ..settings import settings
from .heuristic import extract_heuristic
from .llm import LLMExtractionError, extract_llm


class ExtractionError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def resolve_mode(requested: str = "auto") -> str:
    mode = settings.extractor_backend if requested == "auto" else requested
    mode = (mode or "").lower()
    if mode not in {"heuristic", "llm"}:
        raise ExtractionError(
            "invalid_extractor",
            "EXTRACTOR_BACKEND 只能是 heuristic 或 llm",
        )
    return mode


async def extract_pages(
    document_id: str,
    filename: str,
    pages: list[str],
    mode: str = "auto",
) -> PaperExtraction:
    resolved = resolve_mode(mode)
    if resolved == "heuristic":
        return extract_heuristic(document_id, filename, pages)
    try:
        return await extract_llm(document_id, filename, pages)
    except LLMExtractionError as exc:
        raise ExtractionError(exc.code, str(exc), retryable=exc.retryable) from exc


async def extract_document(
    document_id: str,
    filename: str,
    path: Path,
    mode: str = "auto",
) -> PaperExtraction:
    pages = read_pdf_pages(path)
    return await extract_pages(document_id, filename, pages, mode)


def evidence_counts(paper: PaperExtraction) -> dict[str, int]:
    """Count verified vs rejected evidence for logs and the UI."""
    evidence = [
        item
        for field in (paper.metadata.title, paper.metadata.authors, paper.metadata.year, paper.metadata.venue)
        for item in field.evidence
    ]
    for method in paper.methods:
        evidence.extend(method.evidence)
    for dataset in paper.datasets:
        evidence.extend(dataset.evidence)
    for graph in paper.graph_constructions:
        evidence.extend(graph.evidence)
    for condition in paper.experiment_conditions:
        evidence.extend(condition.evidence)
    for metric in paper.metrics:
        evidence.extend(metric.evidence)
    return {
        "evidence_total": len(evidence),
        "evidence_verified": sum(1 for item in evidence if item.accepted),
        "rejected": len(paper.rejections),
        "missing_fields": len(paper.missing_fields),
    }
