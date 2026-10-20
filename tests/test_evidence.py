from __future__ import annotations

from spectrascholar.evidence import (
    PDFExtractionError,
    make_evidence_ref,
    normalized,
    quote_on_page,
    read_pdf_pages,
    verify_evidence,
    verify_metric,
)
from spectrascholar.schemas import Evidence, MetricEvidence


def test_exact_quote_verified():
    pages = ["We evaluated on Indian Pines dataset with an OA of 98.4%. "]
    good = Evidence(value="Indian Pines", quote="Indian Pines", page=1)
    assert verify_evidence(good, pages).verified is True
    assert verify_evidence(Evidence(value="Indian Pines", quote="Indian Pines", page=2), pages) is None


def test_hallucinated_value_is_rejected():
    pages = ["The OA score is 88.5% on this benchmark."]
    fake = MetricEvidence(dataset="Sample", metric="OA", value="99.9%", page=1, quote="The OA score is 88.5%")
    assert verify_metric(fake, pages) is None
    assert not quote_on_page(pages, 1, "The OA score is 99.9%")


def test_new_evidence_status_model():
    pages = ["We evaluated on Indian Pines dataset with an OA of 98.4%."]
    assert normalized("  Indian   Pines ") == "indian pines"
    assert make_evidence_ref("d", pages, 1, "Indian Pines", "Indian Pines").status == "verified_quote"
    assert make_evidence_ref("d", pages, 1, "missing quote").status == "quote_not_found"
    assert make_evidence_ref("d", pages, 3, "Indian Pines").status == "page_missing"
    assert make_evidence_ref("d", pages, 1, "Indian Pines", "99.9%").status == "quote_found_value_mismatch"


def test_read_pdf_pages_rejects_missing_file():
    from spectrascholar.settings import settings

    try:
        read_pdf_pages(settings.workspace / "missing.pdf")
    except PDFExtractionError as exc:
        assert exc.code == "file_missing"
    else:  # pragma: no cover
        raise AssertionError("expected PDFExtractionError")
