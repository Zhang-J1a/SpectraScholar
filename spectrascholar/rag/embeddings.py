"""Embedding providers.

``hash`` is a deterministic lexical hashing embedder used to keep the whole
pipeline runnable offline.  It is **not** a semantic model; the UI and the
evaluation report must label it as such.  Set ``EMBEDDING_BACKEND=openai`` for
real semantic embeddings.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
import os
from collections import Counter
from typing import Protocol

import httpx

from ..settings import settings
from .bm25 import tokenize


class EmbeddingError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class Embedder(Protocol):
    name: str
    dim: int | None

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Signed hashing of lexical tokens; deterministic and dependency-free."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.name = f"hash-{dim}"

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        counts = Counter(tokenize(text))
        for token, count in counts.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "little")
            index = value % self.dim
            sign = 1.0 if (value >> 8) & 1 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]


class OpenAIEmbedder:
    def __init__(
        self,
        model: str,
        batch_size: int = 32,
        timeout: float = 60.0,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.batch_size = max(1, batch_size)
        self.timeout = timeout
        self.name = f"openai-compatible:{model}"
        self.dim = None
        self._client = None
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip()

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        key = (
            self.api_key
            or os.getenv("EMBEDDING_API_KEY", "").strip()
            or os.getenv("OPENAI_API_KEY", "").strip()
        )
        if not key:
            raise EmbeddingError(
                "missing_api_key",
                "EMBEDDING_BACKEND=openai 需要 EMBEDDING_API_KEY（或 OPENAI_API_KEY）；"
                "可改用 EMBEDDING_BACKEND=hash 进行离线流程测试。",
            )
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=key,
            base_url=(
                self.base_url
                or os.getenv("EMBEDDING_BASE_URL", "").strip()
                or os.getenv("OPENAI_BASE_URL", "").strip()
                or None
            ),
            timeout=self.timeout,
        )
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._client_or_raise()
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            last_error: Exception | None = None
            for attempt in range(1, 3):
                try:
                    response = await client.embeddings.create(model=self.model, input=batch)
                    vectors.extend([list(item.embedding) for item in response.data])
                    break
                except Exception as exc:
                    last_error = exc
                    name = type(exc).__name__.lower()
                    if ("rate" in name or "timeout" in name or "connection" in name) and attempt < 2:
                        await asyncio.sleep(1.5 * attempt)
                        continue
                    raise EmbeddingError(
                        "embedding_provider_error",
                        f"Embedding 调用失败: {str(exc)[:300]}",
                        retryable="rate" in name or "timeout" in name,
                    ) from exc
            if len(vectors) < start + len(batch):
                raise EmbeddingError(
                    "embedding_incomplete",
                    f"Embedding 返回数量不足: {last_error}",
                )
        if vectors:
            self.dim = len(vectors[0])
        return vectors


class OllamaEmbedder:
    """Native Ollama embeddings via ``POST /api/embeddings``.

    This avoids depending on Ollama's OpenAI-compatible layer.  The endpoint
    accepts one prompt at a time; batching is explicit so 4 GB machines do not
    hold a large request in memory.
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 60.0,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"
        self.dim = None
        self._client = client

    async def _embed_one(self, client: httpx.AsyncClient, text: str) -> list[float]:
        last_error: Exception | None = None
        for attempt in range(1, 3):
            try:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                if response.status_code == 404:
                    # Older/alternate Ollama builds can expose only /v1.
                    response = await client.post(
                        f"{self.base_url}/v1/embeddings",
                        json={"model": self.model, "input": text},
                    )
                response.raise_for_status()
                payload = response.json()
                vector = payload.get("embedding")
                if vector is None and payload.get("data"):
                    vector = payload["data"][0].get("embedding")
                if not isinstance(vector, list) or not vector:
                    raise EmbeddingError("ollama_invalid_response", "Ollama 未返回 embedding")
                return [float(value) for value in vector]
            except EmbeddingError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2 and isinstance(
                    exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)
                ):
                    await asyncio.sleep(1.5 * attempt)
                    continue
                break
        raise EmbeddingError(
            "ollama_unavailable",
            f"Ollama embedding 失败（model={self.model}, url={self.base_url}）: "
            f"{type(last_error).__name__}: {str(last_error)[:300]}",
            retryable=True,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._client
        owns_client = client is None
        if client is None:
            client = httpx.AsyncClient(timeout=self.timeout)
        assert client is not None
        try:
            vectors = [await self._embed_one(client, text) for text in texts]
        finally:
            if owns_client:
                await client.aclose()
        if vectors:
            self.dim = len(vectors[0])
        return vectors


def get_embedder(name: str | None = None) -> Embedder:
    backend = (name or settings.embedding_backend).lower()
    if backend == "hash":
        return HashEmbedder(settings.embedding_dim)
    if backend == "openai":
        return OpenAIEmbedder(
            settings.embedding_model,
            batch_size=settings.embedding_batch_size,
            timeout=settings.extraction_timeout_seconds,
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url,
        )
    if backend == "ollama":
        return OllamaEmbedder(
            settings.ollama_embedding_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        )
    raise EmbeddingError(
        "invalid_embedding_backend",
        "EMBEDDING_BACKEND 只能是 hash、openai 或 ollama",
    )
