from __future__ import annotations

from spectrascholar.citations import audit_claims, audit_report, render_audit_markdown


def _resolver(document_id: str):
    if document_id != "d1":
        return None, None
    return {"filename": "paper.pdf"}, ["OA is 98.4% on Indian Pines."]


def test_claim_audit_maps_supported_page_only_external_and_missing():
    report = (
        "OA is 98.4% on Indian Pines "
        '[[doc:d1 p.1 "OA is 98.4% on Indian Pines."]]\n'
        "OA is 97.1% on Indian Pines [[doc:d1 p.1]]\n"
        "The method outperforms the baseline [source](https://example.com/paper)\n"
        "A 42% improvement is reported without citation.\n"
    )
    claims = audit_claims(report, _resolver)
    statuses = {claim.status for claim in claims}
    assert "supported_quote" in statuses
    assert "page_only" in statuses
    assert "external_unchecked" in statuses
    assert "no_citation" in statuses

    supported = next(claim for claim in claims if claim.status == "supported_quote")
    assert supported.document_id == "d1"
    assert supported.page == 1
    assert "98.4" in supported.quote


def test_claim_audit_rejects_quote_not_on_page():
    report = (
        "OA is 99.9% on Indian Pines "
        '[[doc:d1 p.1 "OA is 99.9% on Indian Pines."]]\n'
    )
    claims = audit_claims(report, _resolver)
    assert len(claims) == 1
    assert claims[0].status == "citation_failed"
    assert claims[0].kind == "local_pdf"


def test_citation_audit_contains_claim_counts_and_markdown():
    report = (
        "OA is 98.4% on Indian Pines "
        '[[doc:d1 p.1 "OA is 98.4% on Indian Pines."]]\n'
        "A 42% improvement is reported without citation.\n"
    )
    audit = audit_report(report, _resolver)
    assert audit.claims_supported >= 1
    assert audit.claims_no_citation >= 1
    rendered = render_audit_markdown(audit)
    assert "Claim-level" in rendered
    assert "逐字支持" in rendered
