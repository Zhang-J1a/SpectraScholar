from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import spectrascholar.tools.arxiv_search as arxiv_tool
from spectrascholar.api import tools as tools_api
from spectrascholar.tools.arxiv_search import ArxivSearchError, search_arxiv


class FakeClient:
    calls: list[dict] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        FakeClient.calls.append(kwargs)

    def results(self, search):
        FakeClient.last_search = search
        return iter(self.results_data)


def _result(arxiv_id: str, title: str, doi: str | None, year: int = 2024):
    published = datetime(year, 1, 1, tzinfo=UTC)
    return SimpleNamespace(
        entry_id=f"https://arxiv.org/abs/{arxiv_id}v1",
        get_short_id=lambda: f"{arxiv_id}v1",
        title=title,
        authors=["Alice", "Bob"],
        published=published,
        doi=doi,
        summary="hyperspectral classification with graph neural networks",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        categories=["cs.CV"],
        primary_category="cs.CV",
        journal_ref=None,
    )


def _fake_arxiv(results):
    class Client(FakeClient):
        results_data = results

    return SimpleNamespace(
        Client=Client,
        Search=lambda **kwargs: SimpleNamespace(**kwargs),
        SortCriterion=SimpleNamespace(SubmittedDate="submitted", Relevance="relevance"),
        SortOrder=SimpleNamespace(Descending="descending"),
    )


def test_search_arxiv_builds_filters_and_dedupes_doi(monkeypatch):
    results = [
        _result("2401.00001", "Hyperspectral graph learning", "10.1234/ABC"),
        _result("2401.00002", "Duplicate DOI paper", "https://doi.org/10.1234/abc"),
        _result("2401.00003", "Other paper", None),
    ]
    monkeypatch.setattr(arxiv_tool, "arxiv", _fake_arxiv(results))

    payload = search_arxiv(
        "graph neural network",
        year_from=2020,
        year_to=2024,
        task_topic="hyperspectral classification",
        start=0,
        max_results=10,
    )
    assert payload["provider"] == "arxiv"
    assert "submittedDate:[202001010000 TO 202412312359]" in payload["effective_query"]
    assert "all:graph AND all:neural AND all:network" in payload["effective_query"]
    assert "all:hyperspectral AND all:classification" in payload["effective_query"]
    assert payload["duplicates_filtered"] == 1
    assert payload["returned"] == 2
    assert payload["attempts"] == 1
    assert payload["papers"][0]["doi"] == "10.1234/abc"
    assert payload["papers"][0]["year"] == 2024
    assert payload["papers"][0]["task_topic_match"] is True


def test_search_arxiv_returns_empty_page_without_fake_success(monkeypatch):
    monkeypatch.setattr(arxiv_tool, "arxiv", _fake_arxiv([]))
    payload = search_arxiv("nothing", max_results=5)
    assert payload["returned"] == 0
    assert payload["papers"] == []
    assert payload["has_more"] is False


def test_arxiv_endpoint_returns_structured_tool_result(client, monkeypatch):
    fake_payload = {
        "query": "graph",
        "effective_query": "graph",
        "year_from": 2020,
        "year_to": 2024,
        "task_topic": "hyperspectral",
        "start": 0,
        "max_results": 5,
        "returned": 1,
        "has_more": False,
        "duplicates_filtered": 0,
        "attempts": 1,
        "provider": "arxiv",
        "papers": [
            {
                "arxiv_id": "2401.00001",
                "title": "Paper",
                "authors": ["A"],
                "published": "2024-01-01T00:00:00+00:00",
                "year": 2024,
                "doi": None,
                "abstract": "abstract",
                "pdf_url": None,
                "entry_url": "https://arxiv.org/abs/2401.00001",
                "categories": ["cs.CV"],
                "primary_category": "cs.CV",
                "journal_ref": None,
                "task_topic_match": True,
            }
        ],
    }
    monkeypatch.setattr(tools_api, "search_arxiv", lambda *args, **kwargs: fake_payload)
    response = client.get(
        "/api/v1/tools/arxiv_search",
        params={"query": "graph neural network", "year_from": 2020, "year_to": 2024},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tool"] == "arxiv_search"
    assert body["papers"][0]["arxiv_id"] == "2401.00001"


def test_arxiv_endpoint_rejects_bad_year_range(client):
    response = client.get(
        "/api/v1/tools/arxiv_search",
        params={"query": "graph", "year_from": 2024, "year_to": 2020},
    )
    assert response.status_code == 422


def test_arxiv_tool_reports_missing_dependency(monkeypatch):
    monkeypatch.setattr(arxiv_tool, "arxiv", None)
    with pytest.raises(ArxivSearchError) as error:
        search_arxiv("graph")
    assert error.value.code == "arxiv_unavailable"
