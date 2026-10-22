"""A lightweight, persistable hybrid index (vector + BM25 + RRF).

Why not FAISS/pgvector in v1?
    * The personal corpus is small.
    * A JSON manifest plus in-memory cosine search is inspectable and testable.
    * The interface (``add_document`` / ``search``) is storage-agnostic, so a
      pgvector backend can replace this module later without touching the API.

The manifest never contains API keys.  Vectors are stored as base64 float32 to
keep the file compact while remaining dependency-free.
"""
from __future__ import annotations

import base64
import json
import math
import threading
from array import array
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from .bm25 import BM25, tokenize
from .chunking import Chunk
from .table_meta import table_boost


@dataclass
class StoredChunk:
    chunk_id: str
    document_id: str
    filename: str
    page: int
    text: str
    start: int
    end: int
    vector: list[float] = field(default_factory=list, repr=False)


def _pack(vector: list[float]) -> str:
    values = array("f", vector)
    return base64.b64encode(values.tobytes()).decode("ascii")


def _unpack(payload: str) -> list[float]:
    raw = base64.b64decode(payload.encode("ascii"))
    values = array("f")
    values.frombytes(raw)
    return list(values)


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


class KnowledgeIndex:
    def __init__(self, path: Path, embedding_name: str) -> None:
        self.path = path
        self.embedding_name = embedding_name
        self.chunks: list[StoredChunk] = []
        self.vectors: list[list[float]] = []
        self._bm25: BM25 | None = None
        self._lock = threading.RLock()
        self._loaded = False
        self.manifest_embedding: str | None = None
        self.updated_at: str | None = None
        self.compatible = True

    # -- persistence -----------------------------------------------------
    def _rebuild(self) -> None:
        self._bm25 = BM25([tokenize(chunk.text) for chunk in self.chunks])
        self.vectors = [chunk.vector for chunk in self.chunks]

    def load(self, force: bool = False) -> bool:
        with self._lock:
            if self._loaded and not force:
                return self.compatible
            self.chunks = []
            self.vectors = []
            self.manifest_embedding = None
            self.updated_at = None
            self.compatible = True
            if not self.path.is_file():
                self._bm25 = None
                self._loaded = True
                return True
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.compatible = False
                self._bm25 = None
                self._loaded = True
                return False
            self.manifest_embedding = data.get("embedding")
            self.updated_at = data.get("updated_at")
            if data.get("version") != 1 or self.manifest_embedding != self.embedding_name:
                # The index was built with another embedding backend.  Keep the
                # file untouched, but refuse to mix incompatible vectors.
                self.compatible = False
                self._bm25 = None
                self._loaded = True
                return False
            for item in data.get("chunks", []):
                try:
                    chunk = StoredChunk(
                        chunk_id=str(item["chunk_id"]),
                        document_id=str(item["document_id"]),
                        filename=str(item.get("filename", "")),
                        page=int(item["page"]),
                        text=str(item["text"]),
                        start=int(item.get("start", 0)),
                        end=int(item.get("end", 0)),
                        vector=_unpack(item["vector"]),
                    )
                except (KeyError, TypeError, ValueError, base64.binascii.Error):
                    continue
                self.chunks.append(chunk)
            self._rebuild()
            self._loaded = True
            return True

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.updated_at = datetime.now(UTC).isoformat(timespec="seconds")
            self.manifest_embedding = self.embedding_name
            self.compatible = True
            payload = {
                "version": 1,
                "embedding": self.embedding_name,
                "dim": len(self.chunks[0].vector) if self.chunks else None,
                "updated_at": self.updated_at,
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "filename": chunk.filename,
                        "page": chunk.page,
                        "text": chunk.text,
                        "start": chunk.start,
                        "end": chunk.end,
                        "vector": _pack(chunk.vector),
                    }
                    for chunk in self.chunks
                ],
            }
            temp = self.path.with_suffix(".tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            temp.replace(self.path)

    # -- corpus management ----------------------------------------------
    def add_document(self, document_id: str, filename: str, chunks: list[Chunk], vectors: list[list[float]]) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")
        if any(not vector for vector in vectors):
            raise ValueError("存在空向量，拒绝写入索引")
        with self._lock:
            self.load()
            self.remove_document(document_id, persist=False)
            for chunk, vector in zip(chunks, vectors, strict=True):
                self.chunks.append(
                    StoredChunk(
                        chunk_id=chunk.chunk_id,
                        document_id=document_id,
                        filename=filename,
                        page=chunk.page,
                        text=chunk.text,
                        start=chunk.start,
                        end=chunk.end,
                        vector=list(vector),
                    )
                )
            self._rebuild()
            self.save()
            return len(chunks)

    def replace_all(self, records: list[StoredChunk]) -> int:
        with self._lock:
            self.chunks = list(records)
            self._rebuild()
            self.save()
            return len(self.chunks)

    def remove_document(self, document_id: str, *, persist: bool = True) -> int:
        with self._lock:
            self.load()
            before = len(self.chunks)
            self.chunks = [chunk for chunk in self.chunks if chunk.document_id != document_id]
            removed = before - len(self.chunks)
            if removed:
                self._rebuild()
                if persist:
                    self.save()
            return removed

    def clear(self) -> None:
        with self._lock:
            self.chunks = []
            self.vectors = []
            self._bm25 = None
            self._loaded = True
            self.manifest_embedding = None
            self.updated_at = None
            self.compatible = True
            self.path.unlink(missing_ok=True)

    def stats(self) -> dict:
        with self._lock:
            self.load()
            documents = {chunk.document_id for chunk in self.chunks}
            return {
                "total_chunks": len(self.chunks),
                "documents": len(documents),
                "embedding": self.embedding_name,
                "manifest_embedding": self.manifest_embedding,
                "compatible": self.compatible,
                "updated_at": self.updated_at,
            }

    def documents(self) -> dict[str, int]:
        with self._lock:
            self.load()
            counts: dict[str, int] = {}
            for chunk in self.chunks:
                counts[chunk.document_id] = counts.get(chunk.document_id, 0) + 1
            return counts

    # -- search ----------------------------------------------------------
    def _allowed_indices(self, document_ids: list[str] | None) -> set[int] | None:
        if not document_ids:
            return None
        allowed = set(document_ids)
        return {index for index, chunk in enumerate(self.chunks) if chunk.document_id in allowed}

    def search(
        self,
        query: str,
        query_vector: list[float],
        *,
        mode: str = "hybrid",
        top_k: int = 6,
        document_ids: list[str] | None = None,
        rerank: str = "lexical",
    ) -> list[dict]:
        with self._lock:
            self.load()
            if not self.chunks:
                return []
            allowed = self._allowed_indices(document_ids)
            indices = range(len(self.chunks)) if allowed is None else allowed
            if not indices:
                return []
            bm25_scores = self._bm25.scores(query) if self._bm25 else [0.0] * len(self.chunks)
            vector_scores = [
                _cosine(query_vector, chunk.vector) if index in indices else 0.0
                for index, chunk in enumerate(self.chunks)
            ]
            bm25_scores = [
                score if index in indices else 0.0 for index, score in enumerate(bm25_scores)
            ]

            pool_size = max(top_k * 8, 40)
            vector_ranked = sorted(
                ((index, vector_scores[index]) for index in indices if vector_scores[index] > 0),
                key=lambda item: item[1],
                reverse=True,
            )[:pool_size]
            bm25_ranked = sorted(
                ((index, bm25_scores[index]) for index in indices if bm25_scores[index] > 0),
                key=lambda item: item[1],
                reverse=True,
            )[:pool_size]
            if mode == "vector":
                candidates = {index for index, _ in vector_ranked}
            elif mode == "bm25":
                candidates = {index for index, _ in bm25_ranked}
            else:
                candidates = {index for index, _ in vector_ranked} | {index for index, _ in bm25_ranked}
            if not candidates:
                return []

            vector_rank = {index: rank for rank, (index, _) in enumerate(vector_ranked, 1)}
            bm25_rank = {index: rank for rank, (index, _) in enumerate(bm25_ranked, 1)}
            query_terms = set(tokenize(query))
            max_vector = max((vector_scores[index] for index in candidates), default=1.0) or 1.0
            max_bm25 = max((bm25_scores[index] for index in candidates), default=1.0) or 1.0
            page_texts: dict[tuple[str, int], list[str]] = {}
            for chunk in self.chunks:
                page_texts.setdefault((chunk.document_id, chunk.page), []).append(chunk.text)

            scored: list[dict] = []
            for index in candidates:
                chunk = self.chunks[index]
                vector_score = vector_scores[index]
                bm25_score = bm25_scores[index]
                rrf = 0.0
                if index in vector_rank:
                    rrf += 1.0 / (60 + vector_rank[index])
                if index in bm25_rank:
                    rrf += 1.0 / (60 + bm25_rank[index])
                if mode == "vector":
                    score = vector_score
                elif mode == "bm25":
                    score = bm25_score
                else:
                    score = 0.5 * (vector_score / max_vector) + 0.5 * (bm25_score / max_bm25)
                    if rerank == "lexical" and query_terms:
                        coverage = len(query_terms & set(tokenize(chunk.text))) / len(query_terms)
                        score += 0.1 * coverage
                page_text = "\n".join(page_texts.get((chunk.document_id, chunk.page), []))
                score += table_boost(query, page_text) * max(max_vector, max_bm25)
                scored.append(
                    {
                        "chunk": chunk,
                        "score": score,
                        "vector_score": vector_score,
                        "bm25_score": bm25_score,
                        "rrf_score": rrf,
                    }
                )
            scored.sort(key=lambda item: item["score"], reverse=True)
            return scored[:top_k]
