from __future__ import annotations

import pytest

from spectrascholar.rag.embeddings import EmbeddingError, OpenAIEmbedder


def test_embedding_key_can_be_separate_from_chat_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("EMBEDDING_API_KEY", "embedding-test-key")
    embedder = OpenAIEmbedder("test-embed", api_key="embedding-test-key")
    client = embedder._client_or_raise()
    assert client.api_key == "embedding-test-key"


def test_embedding_provider_missing_key_is_explicit(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    embedder = OpenAIEmbedder("test-embed")
    with pytest.raises(EmbeddingError) as error:
        embedder._client_or_raise()
    assert error.value.code == "missing_api_key"
