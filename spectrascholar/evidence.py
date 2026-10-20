"""PDF reading and deterministic quote verification.

The verifier in this module answers exactly one question: *do these characters
appear on this page?*  It deliberately does not claim that the sentence supports
the scientific conclusion, that the experiment is comparable, or that the paper
is correct.  Those are separate, explicitly labelled checks.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .schemas import Evidence, EvidenceRef, MetricEvidence
from .settings import settings


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot be opened or decoded safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def normalized(text: str) -> str:
    """Case-fold and collapse whitespace so PDF line breaks do not matter."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def quote_on_page(pages: list[str], page: int, quote: str) -> bool:
    return (
        bool(quote and quote.strip())
        and isinstance(page, int)
        and 1 <= page <= len(pages)
        and normalized(quote) in normalized(pages[page - 1])
    )


def page_text_or_empty(pages: list[str], page: int) -> str:
    if isinstance(page, int) and 1 <= page <= len(pages):
        return pages[page - 1]
    return ""


def make_evidence_ref(
    document_id: str,
    pages: list[str],
    page: int | None,
    quote: str | None,
    value: str | None = None,
    *,
    semantic_checked: bool = False,
    note: str | None = None,
) -> EvidenceRef:
    """Build an evidence reference and record the strongest proof achieved."""
    if page is None or page < 1 or page > len(pages):
        return EvidenceRef(
            document_id=document_id,
            page=page,
            quote=quote,
            value=value,
            status="page_missing",
            verification="none",
            semantic_checked=semantic_checked,
            note=note or "页码不在 PDF 有效范围内",
        )
    if not quote or not quote.strip():
        return EvidenceRef(
            document_id=document_id,
            page=page,
            quote=quote,
            value=value,
            status="verified_page_only",
            verification="page",
            semantic_checked=False,
            note=note or "只确认页码存在，未提供原文片段",
        )
    if not quote_on_page(pages, page, quote):
        return EvidenceRef(
            document_id=document_id,
            page=page,
            quote=quote,
            value=value,
            status="quote_not_found",
            verification="none",
            semantic_checked=False,
            note=note or "该原文片段未出现在指定页码",
        )
    if value and normalized(value) not in normalized(quote):
        return EvidenceRef(
            document_id=document_id,
            page=page,
            quote=quote,
            value=value,
            status="quote_found_value_mismatch",
            verification="quote",
            semantic_checked=False,
            note=note or "原文存在，但字段值未在原文片段中逐字出现",
        )
    return EvidenceRef(
        document_id=document_id,
        page=page,
        quote=quote,
        value=value,
        status="verified_quote",
        verification="quote",
        semantic_checked=semantic_checked,
        note=note,
    )


def verify_evidence(item: Evidence, pages: list[str]) -> Evidence | None:
    """Legacy helper: exact quote + value containment, otherwise reject."""
    if not quote_on_page(pages, item.page, item.quote):
        return None
    if item.value.strip() and normalized(item.value) not in normalized(item.quote):
        return None
    return item.model_copy(update={"verified": True})


def verify_metric(item: MetricEvidence, pages: list[str]) -> MetricEvidence | None:
    """Legacy helper: a metric needs a non-empty value found in the quote."""
    if not quote_on_page(pages, item.page, item.quote):
        return None
    if not item.value.strip() or normalized(item.value) not in normalized(item.quote):
        return None
    return item.model_copy(update={"verified": True})


def read_pdf_pages(
    path: Path,
    *,
    max_pages: int | None = None,
    max_chars: int | None = None,
) -> list[str]:
    """Read up to ``max_pages`` pages of text.

    Raises :class:`PDFExtractionError` with a stable ``code`` instead of leaking
    pypdf internals to the API layer.
    """
    if not path.is_file():
        raise PDFExtractionError("file_missing", f"PDF 文件不存在: {path.name}")
    max_pages = settings.max_pdf_pages if max_pages is None else max_pages
    max_chars = settings.max_extract_chars if max_chars is None else max_chars
    try:
        # Read into memory so Windows does not keep a file lock on the upload.
        reader = PdfReader(BytesIO(path.read_bytes()))
    except PdfReadError as exc:
        raise PDFExtractionError("pdf_unreadable", f"无法解析 PDF: {exc}") from exc
    except Exception as exc:  # pragma: no cover - depends on malformed files
        raise PDFExtractionError("pdf_unreadable", f"无法打开 PDF: {exc}") from exc

    if reader.is_encrypted:
        try:
            # Empty-password PDFs still open; real encrypted PDFs do not.
            if reader.decrypt("") == 0:
                raise PDFExtractionError("pdf_encrypted", "PDF 已加密，无法提取文本")
        except PDFExtractionError:
            raise
        except Exception as exc:
            raise PDFExtractionError("pdf_encrypted", f"PDF 已加密: {exc}") from exc

    pages: list[str] = []
    for page in list(reader.pages)[:max_pages]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append(text[:max_chars])
    if not pages:
        raise PDFExtractionError("pdf_empty", "PDF 中没有可读取的页面")
    return pages


def pdf_page_count(path: Path) -> int:
    try:
        reader = PdfReader(BytesIO(path.read_bytes()))
        return len(reader.pages)
    except Exception:
        return 0


def title_hint(pages: list[str]) -> str | None:
    """Best-effort layout hint, not a verified bibliographic title."""
    if not pages:
        return None
    for line in pages[0].splitlines()[:12]:
        candidate = line.strip()
        if not 8 <= len(candidate) <= 300:
            continue
        lowered = candidate.lower()
        if lowered.startswith(("arxiv:", "doi:", "http", "www.", "abstract", "keywords")):
            continue
        if "@" in candidate or re.fullmatch(r"[\d\s.,:-]+", candidate):
            continue
        letters = sum(char.isalpha() for char in candidate)
        if letters < 8:
            continue
        return " ".join(candidate.split())
    return None


def snippet_around(text: str, start: int, end: int, window: int = 220) -> str:
    """Return a contiguous original substring around a match (page-safe)."""
    left = max(0, start - window)
    right = min(len(text), end + window)
    # Do not cut in the middle of a word when it is easy to avoid.
    while left > 0 and text[left - 1].isalnum():
        left -= 1
    while right < len(text) and text[right].isalnum():
        right += 1
    return " ".join(text[left:right].split())


def contains_literal(page: str, value: str) -> bool:
    return bool(value.strip()) and normalized(value) in normalized(page)
