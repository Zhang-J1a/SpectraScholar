from __future__ import annotations

import asyncio

import httpx
import pytest

from spectrascholar.rag.embeddings import EmbeddingError, OllamaEmbedder, OpenAIEmbedder


def test_embedding_key_can_be_separate_from_chat_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-test-key")
    embedder = OpenAIEmbedder("test-embed", api_key="embedding-test-key")
    client = embedder._client_or_raise()
    assert client.api_key == "embedding-test-key"


def test_ollama_native_embeddings_use_api_endpoint():
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        calls.append(__import__("json").loads(request.content))
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    embedder = OllamaEmbedder("nomic-embed-text", client=client)
    vectors = asyncio.run(embedder.embed(["first", "second"]))
    asyncio.run(client.aclose())
    assert vectors == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert embedder.dim == 3
    assert calls == [
        {"model": "nomic-embed-text", "prompt": "first"},
        {"model": "nomic-embed-text", "prompt": "second"},
    ]


def test_embedding_provider_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    embedder = OpenAIEmbedder("test-embed")
    with pytest.raises(EmbeddingError) as error:
        embedder._client_or_raise()
    assert error.value.code == "missing_api_key"
