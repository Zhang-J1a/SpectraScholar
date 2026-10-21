from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from spectrascholar.extraction import ocr as ocr_module
from spectrascholar.extraction.ocr import OCRError, augment_pages_with_ocr, select_ocr_pages
from spectrascholar.settings import settings


def test_select_ocr_pages_only_low_text_table_pages():
    pages = [
        "TABLE VI\nno numeric table text",
        "prose page without a table",
        "TABLE II\n99.1 98.2 97.3 96.4 95.5 94.6 93.7 92.8 91.9",
    ]
    assert select_ocr_pages(pages, max_pages=2) == [1]


def test_ocr_disabled_is_noop(monkeypatch):
    monkeypatch.setattr(ocr_module, "settings", replace(settings, ocr_enabled=False))
    pages = ["TABLE VI\nno numeric text"]
    unchanged, notes = augment_pages_with_ocr(pages, Path("missing.pdf"))
    assert unchanged == pages
    assert notes == []


def test_ocr_unavailable_returns_note(monkeypatch):
    monkeypatch.setattr(
        ocr_module,
        "settings",
        replace(settings, ocr_enabled=True, ocr_max_pages=1),
    )

    def fail():
        raise OCRError("ocr_unavailable", "no tesseract")

    monkeypatch.setattr(ocr_module, "_load_tesseract", fail)
    pages, notes = augment_pages_with_ocr(["TABLE VI\nno numeric text"], Path("missing.pdf"))
    assert pages == ["TABLE VI\nno numeric text"]
    assert notes and "ocr_unavailable" in notes[0]
