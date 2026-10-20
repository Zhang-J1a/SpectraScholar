from __future__ import annotations

import asyncio
from dataclasses import replace

import spectrascholar.extraction.tables as tables_module
from spectrascholar.evidence import read_pdf_pages
from spectrascholar.extraction.service import extract_document
from spectrascholar.extraction.tables import (
    merge_table_result,
    parse_pdf_tables,
    parse_table_rows,
)
from spectrascholar.schemas import (
    EvidenceRef,
    MetricRecord,
    PaperExtraction,
)
from spectrascholar.settings import settings
from tests.conftest import (
    DYNAMIC_GNN_PAGES,
    make_pdf_bytes,
    make_table_pdf_bytes,
    upload_pdf,
    upload_table_pdf,
)


def _table_pages() -> list[str]:
    return [
        "Table 1: OA on Indian Pines with 10% training samples, patch size 9x9, random split.\n"
        "Method OA AA Kappa\n"
        "HybridSN 98.4 97.8 0.976\n"
        "GCN 97.1 96.5 0.965"
    ]


def test_table_pdf_extracts_method_level_metrics():
    path = settings.workspace / "table_fixture.pdf"
    path.write_bytes(make_table_pdf_bytes())
    paper = asyncio.run(extract_document("doc-table", "table_fixture.pdf", path, "heuristic"))

    assert len(paper.metrics) == 6
    assert all(metric.source == "table" for metric in paper.metrics)
    methods = {metric.method for metric in paper.metrics}
    assert methods == {"HybridSN", "GCN"}
    oa = next(metric for metric in paper.metrics if metric.method == "HybridSN" and metric.metric == "OA")
    assert oa.dataset == "Indian Pines"
    assert oa.value == "98.4"
    assert oa.train_ratio == "10%"
    assert oa.patch_size == "9x9"
    assert oa.protocol == "随机划分/采样"
    assert oa.evidence[0].status == "verified_quote"
    assert [dataset.name for dataset in paper.datasets] == ["Indian Pines"]
    assert paper.datasets[0].evidence[0].status == "verified_quote"
    assert any("表格" in note for note in paper.notes)
    assert paper.rejections == []
    assert paper.stats.accepted >= 7


def test_parse_table_rows_rejects_ambiguous_and_unverifiable_cells():
    rows = [
        ["Method", "OA", "AA", "Kappa"],
        ["A", "98.4/97.1", "97.0", "0.970"],
        ["B", "96.0", "95.0", "0.950"],
    ]
    pages = ["Method OA AA Kappa"]  # deliberately no numeric values on the page
    result = parse_table_rows(
        rows,
        document_id="doc-table",
        page_no=1,
        pages=pages,
        caption="Table 1: Indian Pines with 10% training samples, patch size 9x9.",
        page_text=pages[0],
    )
    assert any(rejection.reason == "ambiguous_table_cell" for rejection in result.rejections)
    assert all(metric.value not in {"98.4/97.1", "97.0", "0.970"} for metric in result.metrics)
    assert result.metrics == []  # B's values are absent from pages, so they are rejected too
    assert any(rejection.reason == "quote_not_found" for rejection in result.rejections)


def test_merge_prefers_table_association_but_keeps_text_conditions():
    existing_metric = MetricRecord(
        dataset="Indian Pines",
        metric="OA",
        value="98.4",
        train_ratio="10%",
        patch_size="9x9",
        protocol=None,
        source="text",
        evidence=[EvidenceRef(document_id="d", page=1, quote="98.4", status="verified_quote")],
    )
    paper = PaperExtraction(
        document_id="d",
        filename="d.pdf",
        metrics=[existing_metric],
        missing_fields=[],
        stats={"pages_scanned": 1},
    )
    table_rows = [["Method", "OA"], ["HybridSN", "98.4"]]
    pages = ["HybridSN 98.4"]
    table = parse_table_rows(
        table_rows,
        document_id="d",
        page_no=1,
        pages=pages,
        caption="Table 1: Indian Pines with 10% training samples.",
        page_text=pages[0],
    )
    merged = merge_table_result(paper, table)
    assert len(merged.metrics) == 1
    metric = merged.metrics[0]
    assert metric.source == "table"
    assert metric.method == "HybridSN"
    assert metric.train_ratio == "10%"
    assert metric.patch_size == "9x9"  # preserved from the text extractor
    assert metric.protocol is None  # never guessed by the table parser


def test_pdf_table_detection_handles_no_table_disabled_and_missing_text(monkeypatch):
    plain = settings.workspace / "plain.pdf"
    plain.write_bytes(make_pdf_bytes([["A plain page without any ruled table."]]))
    pages = read_pdf_pages(plain)
    no_table = parse_pdf_tables(plain, pages, "doc-plain")
    assert no_table.tables_found == 0
    assert any("未检测到结构化表格" in note for note in no_table.notes)

    disabled = replace(settings, table_extraction_enabled=False)
    monkeypatch.setattr(tables_module, "settings", disabled)
    skipped = parse_pdf_tables(plain, pages, "doc-plain")
    assert any("TABLE_EXTRACTION_ENABLED=0" in note for note in skipped.notes)

    monkeypatch.setattr(tables_module, "settings", settings)
    table_pdf = settings.workspace / "table_no_text.pdf"
    table_pdf.write_bytes(make_table_pdf_bytes())
    unreadable = parse_pdf_tables(table_pdf, [""], "doc-table")
    assert unreadable.tables_found == 1
    assert unreadable.metrics == []
    assert any(rejection.reason == "quote_not_found" for rejection in unreadable.rejections)

    missing = parse_pdf_tables(settings.workspace / "missing.pdf", ["x"], "doc-missing")
    assert any("无法打开 PDF" in note for note in missing.notes)


def test_compare_api_exposes_table_source_and_method(client):
    table_doc = upload_table_pdf(client, "table_paper.pdf")
    text_doc = upload_pdf(client, "dynamic_gnn.pdf", DYNAMIC_GNN_PAGES)
    response = client.post(
        "/api/v1/compare",
        json={"document_ids": [table_doc["document_id"], text_doc["document_id"]], "mode": "heuristic"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    table_rows = [row for row in result["metric_rows"] if row["document_id"] == table_doc["document_id"]]
    assert table_rows
    assert all(row["source"] == "table" for row in table_rows)
    assert {row["method"] for row in table_rows} == {"HybridSN", "GCN"}
    assert any(row["metric"] == "OA" and row["dataset"] == "Indian Pines" for row in table_rows)
    assert "来源" in result["markdown"]
    assert "table" in result["markdown"]
