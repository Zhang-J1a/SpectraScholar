"""Extraction service: choose an extractor and load the PDF exactly once."""
from __future__ import annotations

import asyncio
from pathlib import Path

from ..evidence import read_pdf_pages
from ..schemas import PaperExtraction
from ..settings import settings
from .heuristic import extract_heuristic
from .llm import LLMExtractionError, extract_llm
from .ocr import augment_pages_with_ocr
from .tables import (
    merge_table_result,
    parse_pdf_tables,
    parse_text_metric_rows,
    parse_transposed_metric_rows,
)


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
    *,
    pdf_path: Path | None = None,
) -> PaperExtraction:
    ocr_notes: list[str] = []
    if pdf_path is not None and settings.ocr_enabled:
        pages, ocr_notes = await asyncio.to_thread(augment_pages_with_ocr, pages, pdf_path)

    resolved = resolve_mode(mode)
    if resolved == "heuristic":
        paper = extract_heuristic(document_id, filename, pages)
    else:
        try:
            paper = await extract_llm(document_id, filename, pages)
        except LLMExtractionError as exc:
            raise ExtractionError(exc.code, str(exc), retryable=exc.retryable) from exc

    if pdf_path is not None and settings.table_extraction_enabled:
        try:
            table_result = parse_pdf_tables(pdf_path, pages, document_id)
            paper = merge_table_result(paper, table_result)
        except Exception as exc:
            paper.notes.append(f"表格解析失败（已忽略，不影响正文抽取）: {type(exc).__name__}: {exc}")
        try:
            text_rows = parse_text_metric_rows(
                pages,
                document_id,
                [method.name for method in paper.methods],
                paper.experiment_conditions,
            )
            paper = merge_table_result(paper, text_rows)
            transposed = parse_transposed_metric_rows(
                pages,
                document_id,
                [method.name for method in paper.methods],
                paper.experiment_conditions,
            )
            paper = merge_table_result(paper, transposed)
        except Exception as exc:
            paper.notes.append(f"文本表格行解析失败（已忽略）: {type(exc).__name__}: {exc}")
    if ocr_notes:
        paper = paper.model_copy(update={"notes": [*paper.notes, *ocr_notes]})
    return paper


async def extract_document(
    document_id: str,
    filename: str,
    path: Path,
    mode: str = "auto",
) -> PaperExtraction:
    pages = read_pdf_pages(path)
    return await extract_pages(document_id, filename, pages, mode, pdf_path=path)


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
