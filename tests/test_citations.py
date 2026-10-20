from __future__ import annotations

from spectrascholar.citations import (
    append_audit_section,
    audit_report,
    find_unsupported_claims,
    render_audit_markdown,
)


def _resolver(document_id: str):
    if document_id != "d1":
        return None, None
    return (
        {"document_id": "d1", "filename": "paper.pdf"},
        [
            "The OA is 98.4% on Indian Pines.",
            "We use a dynamic graph for classification.",
        ],
    )


def test_audit_verifies_quotes_pages_documents_and_external_links():
    report = (
        "# Report\n\n"
        'The OA is 98.4% on Indian Pines. [[doc:d1 p.1 "The OA is 98.4% on Indian Pines."]]\n\n'
        'A bad quote. [[doc:d1 p.1 "this quote does not exist"]]\n\n'
        'A bad page. [[doc:d1 p.9]]\n\n'
        "A missing document. [[doc:nope p.1]]\n\n"
        "An external source [paper](https://example.com/paper).\n\n"
        "Malformed marker [[doc:d1 p.1\n\n"
        "This sentence claims OA of 99.9% without any citation.\n"
    )
    audit = audit_report(report, _resolver)
    assert audit.verified_local == 1
    assert audit.failed_local == 3
    assert audit.external_unchecked == 1
    assert any(check.status == "quote_not_found" for check in audit.checks)
    assert any(check.status == "page_missing" for check in audit.checks)
    assert any(check.status == "document_missing" for check in audit.checks)
    assert any(check.status == "malformed" for check in audit.checks)
    assert audit.unsupported_claims
    assert all(check.semantic_checked is False for check in audit.checks)

    rendered = render_audit_markdown(audit)
    assert "引用核验报告" in rendered
    assert "未通过的本地引用" in rendered
    assert "原文出现 ≠ 事实正确" in rendered


def test_local_pdf_markdown_link_is_marked_unverified_not_unsupported():
    report = "The OA is 98.4% ([paper.pdf](paper.pdf))."
    audit = audit_report(report, _resolver)
    assert audit.local_file_unverified == 1
    assert audit.failed_local == 0
    assert audit.unsupported_claims == []
    assert audit.checks[0].kind == "local_file"
    assert audit.checks[0].status == "local_file_unverified"


def test_audit_page_only_citation_is_distinguished():
    report = "See page. [[doc:d1 p.2]]"
    audit = audit_report(report, _resolver)
    assert audit.page_only_local == 1
    assert audit.verified_local == 0
    assert audit.failed_local == 0
    assert audit.checks[0].status == "verified_page_only"


def test_claim_with_trailing_page_only_citation_is_not_flagged():
    report = "The OA is 98.4%。[[doc:d1 p.1]]"
    assert find_unsupported_claims(report) == []
    audit = audit_report(report, _resolver)
    assert audit.page_only_local == 1
    assert audit.failed_local == 0


def test_audit_scope_excludes_tables_and_headings_from_claims():
    report = (
        "# OA results\n\n"
        "| paper | OA |\n|---|---|\n| A | 98.4% |\n\n"
        "The result is OA 98.4%. [[doc:d1 p.1 \"The OA is 98.4% on Indian Pines.\"]]\n"
    )
    claims = find_unsupported_claims(report)
    assert claims == []


def test_append_audit_section_is_idempotent():
    audit = audit_report("No citations here.", _resolver)
    first = append_audit_section("# Report", audit)
    second = append_audit_section(first, audit)
    assert first == second
    assert first.count("## 引用核验报告（自动生成）") == 1
