from __future__ import annotations

from dataclasses import replace

import spectrascholar.rag.embeddings as embeddings_module
import spectrascholar.rag.service as rag_service
from spectrascholar.settings import settings


def test_index_search_and_answer_with_page_citations(client, two_papers):
    first, _ = two_papers
    indexed = client.post("/api/v1/kb/index", json={})
    assert indexed.status_code == 200, indexed.text
    payload = indexed.json()
    assert len(payload["indexed_documents"]) == 2
    assert payload["total_chunks"] > 0
    assert payload["embedding_backend"].startswith("hash-")

    search = client.post(
        "/api/v1/kb/search",
        json={"query": "dynamic graph KNN Indian Pines", "top_k": 5, "mode": "hybrid"},
    )
    assert search.status_code == 200
    hits = search.json()["hits"]
    assert hits
    assert hits[0]["document_id"] == first["document_id"]
    assert hits[0]["page"] >= 1
    assert "[[doc:" in hits[0]["citation"]
    assert "hash" in search.json()["note"]

    answer = client.post(
        "/api/v1/kb/answer",
        json={"query": "What accuracy does the dynamic graph method report on Indian Pines?", "top_k": 5},
    )
    assert answer.status_code == 200, answer.text
    result = answer.json()
    assert result["refusal"] is False
    assert result["grounded"] is True
    assert result["citations"]
    assert "[[doc:" in result["answer"]
    assert all(check["semantic_checked"] is False for check in result["citations"])


def test_search_filters_by_document(client, two_papers):
    _, second = two_papers
    assert client.post("/api/v1/kb/index", json={}).status_code == 200
    response = client.post(
        "/api/v1/kb/search",
        json={
            "query": "graph method",
            "top_k": 5,
            "document_ids": [second["document_id"]],
        },
    )
    hits = response.json()["hits"]
    assert hits
    assert all(hit["document_id"] == second["document_id"] for hit in hits)


def test_answer_refuses_on_empty_knowledge_base(client):
    response = client.post(
        "/api/v1/kb/answer",
        json={"query": "What is the best method for hyperspectral classification?"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["refusal"] is True
    assert result["grounded"] is False
    assert result["citations"] == []
    assert "没有找到足够证据" in result["answer"]


def test_index_missing_document_is_reported_not_invented(client):
    response = client.post("/api/v1/kb/index", json={"document_ids": ["missing"]})
    assert response.status_code == 200
    result = response.json()
    assert result["indexed_documents"] == []
    assert result["skipped"][0]["document_id"] == "missing"
    assert result["total_chunks"] == 0


def test_delete_document_removes_chunks(client, two_papers):
    first, _ = two_papers
    assert client.post("/api/v1/kb/index", json={}).status_code == 200
    before = client.get("/api/v1/kb/status").json()["total_chunks"]
    assert before > 0
    assert client.delete(f"/api/v1/documents/{first['document_id']}").status_code == 200
    after = client.get("/api/v1/kb/status").json()["total_chunks"]
    assert after < before


def test_validation_and_clear_endpoint(client, two_papers):
    assert client.post("/api/v1/kb/search", json={"query": "x"}).status_code == 422
    assert client.post("/api/v1/kb/search", json={"query": "valid query", "top_k": 0}).status_code == 422
    assert client.post("/api/v1/kb/search", json={"query": "valid query", "top_k": 21}).status_code == 422
    assert client.post("/api/v1/kb/index", json={}).status_code == 200
    assert client.get("/api/v1/kb/status").json()["total_chunks"] > 0
    cleared = client.delete("/api/v1/kb")
    assert cleared.status_code == 200
    assert client.get("/api/v1/kb/status").json()["total_chunks"] == 0


def test_openai_embedding_without_key_is_503(client, two_papers, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    openai_settings = replace(settings, embedding_backend="openai")
    monkeypatch.setattr(rag_service, "settings", openai_settings)
    monkeypatch.setattr(embeddings_module, "settings", openai_settings)
    rag_service.reset_index()
    response = client.post("/api/v1/kb/index", json={})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]

def test_route_question_selects_metadata_metric_hybrid():
    from spectrascholar.rag.router import route_question
    assert route_question("WFCG 发表于哪一年？") == "bm25"
    assert route_question("Indian Pines 的 OA 是多少？") == "vector"
    assert route_question("比较两种方法的主要区别") == "hybrid"

