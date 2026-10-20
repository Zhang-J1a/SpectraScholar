from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

import spectrascholar.extraction.llm as llm_module
from spectrascholar.evidence import make_evidence_ref
from spectrascholar.extraction.heuristic import extract_heuristic
from spectrascholar.extraction.llm import (
    LLMExtractionError,
    extract_llm,
    parse_json_object,
)
from spectrascholar.extraction.service import ExtractionError, extract_pages, resolve_mode
from tests.conftest import DYNAMIC_GNN_PAGES, HYBRIDSN_PAGES, upload_pdf


def _pages(blocks):
    return ["\n".join(block) for block in blocks]


def test_heuristic_extracts_metadata_methods_datasets_metrics_and_conditions():
    pages = _pages(DYNAMIC_GNN_PAGES)
    paper = extract_heuristic("doc-1", "dynamic_gnn.pdf", pages)

    assert paper.metadata.title.value.startswith("Dynamic Graph Neural Networks")
    assert paper.metadata.authors.value == "Alice Smith, Bob Lee"
    assert paper.metadata.year.value == "2024"
    assert paper.metadata.venue.value.startswith("IGARSS 2024")

    method_names = {method.name for method in paper.methods}
    assert "GCN" in method_names
    assert any(method.family == "GNN" for method in paper.methods)

    dataset_names = {dataset.name for dataset in paper.datasets}
    assert "Indian Pines" in dataset_names

    graph_kinds = {graph.kind for graph in paper.graph_constructions}
    assert "KNN" in graph_kinds
    assert "dynamic" in graph_kinds

    oa = next(metric for metric in paper.metrics if metric.metric == "OA")
    assert oa.value == "98.4%"
    assert oa.dataset == "Indian Pines"
    assert oa.train_ratio == "10%"
    assert oa.patch_size == "9x9"
    assert oa.protocol == "随机划分/采样"
    assert oa.evidence[0].status == "verified_quote"
    assert "98.4" in oa.evidence[0].quote

    kappa = next(metric for metric in paper.metrics if metric.metric == "Kappa")
    assert kappa.value == "0.977"
    assert paper.stats.accepted > 0
    assert paper.stats.rejected == 0
    assert "不补全" in " ".join(paper.notes)


def test_heuristic_never_invents_missing_values():
    paper = extract_heuristic("doc-empty", "blank.pdf", [""])
    assert paper.metadata.title.value is None
    assert paper.metadata.year.value is None
    assert paper.methods == []
    assert paper.datasets == []
    assert paper.metrics == []
    assert "metadata.title" in paper.missing_fields
    assert "metrics" in paper.missing_fields
    assert any("OCR" in note for note in paper.notes)


def test_metric_without_dataset_is_kept_but_not_linked():
    paper = extract_heuristic(
        "doc-2",
        "no-dataset.pdf",
        ["Our method reports an overall accuracy (OA) of 91.2% on the benchmark."],
    )
    metric = paper.metrics[0]
    assert metric.value == "91.2%"
    assert metric.dataset is None
    assert metric.train_ratio is None
    assert metric.evidence[0].status == "verified_quote"


@pytest.mark.parametrize("mode", ["heuristic", "auto"])
def test_extract_pages_service(mode):
    pages = _pages(HYBRIDSN_PAGES)
    paper = asyncio.run(extract_pages("doc-3", "hybridsn.pdf", pages, mode))
    assert paper.extraction_mode == "heuristic"
    assert any(method.name == "HybridSN" for method in paper.methods)
    assert any(metric.metric == "OA" and metric.value == "97.1%" for metric in paper.metrics)


def test_resolve_mode_rejects_invalid(monkeypatch):
    with pytest.raises(ExtractionError):
        resolve_mode("magic")


def test_make_evidence_ref_distinguishes_failure_modes():
    pages = ["The OA is 88.5% on Indian Pines."]
    assert make_evidence_ref("d", pages, 99, "anything").status == "page_missing"
    assert make_evidence_ref("d", pages, 1, "not on this page").status == "quote_not_found"
    mismatch = make_evidence_ref("d", pages, 1, "The OA is 88.5%", value="99.9%")
    assert mismatch.status == "quote_found_value_mismatch"
    ok = make_evidence_ref("d", pages, 1, "The OA is 88.5%", value="88.5%")
    assert ok.status == "verified_quote"
    assert ok.semantic_checked is False


class _FakeCompletions:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


class _FakeClient:
    def __init__(self, content: str, **kwargs):
        self.completions = _FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


def _install_fake_openai(monkeypatch, content: str):
    holder = {}

    def factory(**kwargs):
        client = _FakeClient(content)
        holder["client"] = client
        return client

    monkeypatch.setattr(llm_module, "AsyncOpenAI", factory)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return holder


def _valid_llm_payload():
    quote = "On Indian Pines with 10% training samples and patch size 9x9 under random split,"
    metric_quote = "the overall accuracy (OA) is 98.4% and Kappa is 0.977."
    return {
        "title": {
            "value": "Dynamic Graph Neural Networks for Hyperspectral Image Classification",
            "page": 1,
            "quote": "Dynamic Graph Neural Networks for Hyperspectral Image Classification",
        },
        "authors": {"value": "Alice Smith, Bob Lee", "page": 1, "quote": "Alice Smith, Bob Lee"},
        "year": {"value": "2024", "page": 1, "quote": "IGARSS 2024"},
        "venue": {"value": "IGARSS 2024", "page": 1, "quote": "IGARSS 2024"},
        "methods": [{"name": "GCN", "page": 1, "quote": "using GCN and KNN graph construction"}],
        "datasets": [{"name": "Indian Pines", "page": 2, "quote": quote}],
        "graph_construction": [{"kind": "dynamic", "page": 2, "quote": "The dynamic graph is updated during training."}],
        "conditions": [
            {
                "dataset": "Indian Pines",
                "train_ratio": "10%",
                "patch_size": "9x9",
                "protocol": "random split",
                "page": 2,
                "quote": quote,
            }
        ],
        "metrics": [
            {
                "dataset": "Indian Pines",
                "metric": "OA",
                "value": "98.4%",
                "train_ratio": "10%",
                "patch_size": "9x9",
                "page": 2,
                "quote": metric_quote,
            }
        ],
    }


def test_llm_extraction_accepts_only_verified_candidates(monkeypatch):
    holder = _install_fake_openai(monkeypatch, json.dumps(_valid_llm_payload()))
    paper = asyncio.run(extract_llm("doc-llm", "dynamic_gnn.pdf", _pages(DYNAMIC_GNN_PAGES)))
    assert paper.extraction_mode == "llm"
    assert paper.metadata.title.value.startswith("Dynamic Graph")
    assert paper.methods[0].name == "GCN"
    assert paper.methods[0].family == "GNN"
    assert paper.datasets[0].name == "Indian Pines"
    assert paper.metrics[0].value == "98.4%"
    assert paper.metrics[0].evidence[0].status == "verified_quote"
    assert paper.rejections == []
    assert holder["client"].completions.calls[0]["temperature"] == 0


def test_llm_hallucinated_metric_is_rejected(monkeypatch):
    payload = _valid_llm_payload()
    payload["metrics"][0]["value"] = "99.9%"
    _install_fake_openai(monkeypatch, json.dumps(payload))
    paper = asyncio.run(extract_llm("doc-llm", "dynamic_gnn.pdf", _pages(DYNAMIC_GNN_PAGES)))
    assert paper.metrics == []
    assert paper.rejections
    assert any(
        record.reason in {"quote_found_value_mismatch", "quote_not_found"} for record in paper.rejections
    )
    # Rejected candidates may appear in the audit log, but never as extracted metrics.
    assert all(metric.value != "99.9%" for metric in paper.metrics)


def test_llm_hallucinated_quote_is_rejected(monkeypatch):
    payload = _valid_llm_payload()
    payload["methods"][0]["quote"] = "This sentence does not exist in the PDF."
    _install_fake_openai(monkeypatch, json.dumps(payload))
    paper = asyncio.run(extract_llm("doc-llm", "dynamic_gnn.pdf", _pages(DYNAMIC_GNN_PAGES)))
    assert paper.methods == []
    assert any(record.field == "methods" for record in paper.rejections)


def test_llm_invalid_json_raises_clear_error(monkeypatch):
    _install_fake_openai(monkeypatch, "this is not json at all")
    with pytest.raises(LLMExtractionError) as exc_info:
        asyncio.run(extract_llm("doc-llm", "x.pdf", _pages(DYNAMIC_GNN_PAGES)))
    assert exc_info.value.code == "invalid_json"


def test_llm_missing_key_fails_before_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMExtractionError) as exc_info:
        asyncio.run(extract_llm("doc-llm", "x.pdf", _pages(DYNAMIC_GNN_PAGES)))
    assert exc_info.value.code == "missing_api_key"


def test_parse_json_repairs_code_fence_and_trailing_comma():
    assert parse_json_object('```json\n{"a": 1,}\n```') == {"a": 1}
    with pytest.raises(LLMExtractionError):
        parse_json_object("no braces here")


def test_verify_endpoint(client):
    info = upload_pdf(client, "evidence.pdf", [["The OA is 88.5% on Indian Pines."]])
    good = client.post(
        "/api/v1/evidence/verify",
        json={
            "document_id": info["document_id"],
            "page": 1,
            "quote": "The OA is 88.5%",
            "value": "88.5%",
        },
    )
    assert good.status_code == 200
    assert good.json()["status"] == "verified_quote"
    assert good.json()["semantic_checked"] is False

    bad_page = client.post(
        "/api/v1/evidence/verify",
        json={"document_id": info["document_id"], "page": 9, "quote": "anything"},
    )
    assert bad_page.json()["status"] == "page_missing"

    bad_quote = client.post(
        "/api/v1/evidence/verify",
        json={"document_id": info["document_id"], "page": 1, "quote": "fabricated quote"},
    )
    assert bad_quote.json()["status"] == "quote_not_found"

    missing = client.post(
        "/api/v1/evidence/verify",
        json={"document_id": "nope", "page": 1, "quote": "x"},
    )
    assert missing.status_code == 404
