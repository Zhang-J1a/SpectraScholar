"""Optional, one-page-at-a-time Tesseract OCR for image-only result tables.

The base install stays light. OCR is opt-in via ``OCR_ENABLED=1`` and
``requirements-ocr.txt``. Only pages that look like result tables but have
too little numeric text are rendered. Each page image is released before the
next page is read, which keeps peak memory suitable for a 4 GB machine.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..settings import settings

TABLE_CAPTION_RE = re.compile(r"\b(?:table|tab\.)\s+[ivx\d]", re.IGNORECASE)
NUMERIC_RE = re.compile(r"\d{1,3}(?:\.\d+)?")
MIN_TEXT_NUMBERS = 6


class OCRError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _load_tesseract():
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise OCRError(
            "ocr_unavailable",
            "未安装 pytesseract/Pillow；请先 pip install -r requirements-ocr.txt",
        ) from exc
    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:  # pragma: no cover - binary dependent
        raise OCRError(
            "ocr_unavailable",
            f"找不到 Tesseract 可执行文件: {type(exc).__name__}: {exc}",
        ) from exc
    return pytesseract, Image


def select_ocr_pages(pages: list[str], max_pages: int | None = None) -> list[int]:
    """Return 1-based page numbers that look like image result tables.

    Avoid OCR on prose pages and on tables whose values are already textual.
    """
    limit = settings.ocr_max_pages if max_pages is None else max_pages
    selected: list[int] = []
    for index, text in enumerate(pages, 1):
        if not TABLE_CAPTION_RE.search(text):
            continue
        numbers = len(NUMERIC_RE.findall(text))
        if numbers >= MIN_TEXT_NUMBERS:
            continue
        selected.append(index)
        if len(selected) >= limit:
            break
    return selected


def ocr_pages(pdf_path: Path, page_numbers: list[int]) -> dict[int, str]:
    """OCR selected pages, rendering and releasing one page at a time."""
    if not page_numbers:
        return {}
    pytesseract, Image = _load_tesseract()
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise OCRError("ocr_unavailable", "未安装 pymupdf，无法渲染 PDF 页面") from exc

    result: dict[int, str] = {}
    doc = pymupdf.open(str(pdf_path))
    try:
        for number in page_numbers:
            if number < 1 or number > len(doc):
                continue
            page = doc[number - 1]
            pix = page.get_pixmap(dpi=settings.ocr_dpi, colorspace=pymupdf.csGRAY, alpha=False)
            image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            try:
                text = pytesseract.image_to_string(
                    image,
                    lang=settings.ocr_lang,
                    config=f"--oem 3 --psm {settings.ocr_psm}",
                )
            finally:
                image.close()
                del pix
            if text.strip():
                result[number] = text
    finally:
        doc.close()
    return result


def augment_pages_with_ocr(pages: list[str], pdf_path: Path) -> tuple[list[str], list[str]]:
    """Return page texts with OCR appended, plus notes.

    OCR failure is non-fatal: extraction continues with the original text and
    the note records why the image table was not recovered.
    """
    if not settings.ocr_enabled:
        return pages, []
    selected = select_ocr_pages(pages)
    if not selected:
        return pages, []
    try:
        texts = ocr_pages(pdf_path, selected)
    except OCRError as exc:
        return pages, [f"OCR 未执行：{exc.code}: {exc}"]
    except Exception as exc:  # pragma: no cover - defensive
        return pages, [f"OCR 未执行：{type(exc).__name__}: {exc}"]
    if not texts:
        return pages, [f"OCR 已尝试但无文本：pages={selected}"]

    augmented = list(pages)
    for number, text in texts.items():
        augmented[number - 1] = f"{augmented[number - 1]}\n[OCR PAGE {number}]\n{text}"
    return augmented, [f"OCR 已处理页：{sorted(texts)}（逐页渲染，已释放图片）"]
