"""Structured paper extraction (P1-A)."""
from .service import (
    ExtractionError,
    evidence_counts,
    extract_document,
    extract_pages,
    resolve_mode,
)

__all__ = [
    "ExtractionError",
    "evidence_counts",
    "extract_document",
    "extract_pages",
    "resolve_mode",
]
