"""A small dependency-free BM25 implementation.

The corpus is intentionally small (a personal PDF library), so an in-memory
inverted index is enough.  For a larger corpus, replace this module with a
proper search engine without changing the service interface.
"""
from __future__ import annotations

import math
import re
from collections import Counter

LATIN_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.\-_/][a-z0-9]+)*")
CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "were", "be", "been", "this", "that", "these", "those", "we",
    "our", "it", "as", "by", "from", "at", "which", "can", "using", "based",
    "paper", "method", "results", "show", "shows", "than", "into", "also",
}


def tokenize(text: str) -> list[str]:
    lowered = (text or "").casefold()
    tokens = [token for token in LATIN_TOKEN_RE.findall(lowered) if token not in STOPWORDS]
    cjk_chars = CJK_CHAR_RE.findall(lowered)
    tokens.extend(cjk_chars)
    tokens.extend(cjk_chars[index] + cjk_chars[index + 1] for index in range(len(cjk_chars) - 1))
    return tokens


class BM25:
    def __init__(self, documents: list[list[str]], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.n = len(documents)
        self.term_freqs: list[Counter[str]] = [Counter(document) for document in documents]
        self.doc_lengths = [len(document) for document in documents]
        self.avg_length = (sum(self.doc_lengths) / self.n) if self.n else 0.0
        document_freq: Counter[str] = Counter()
        for frequencies in self.term_freqs:
            document_freq.update(frequencies.keys())
        self.idf = {
            term: math.log(1 + (self.n - freq + 0.5) / (freq + 0.5))
            for term, freq in document_freq.items()
        }

    def scores(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.n:
            return [0.0] * self.n
        results = []
        for index in range(self.n):
            frequency = self.term_freqs[index]
            length = self.doc_lengths[index] or 1
            score = 0.0
            for term in query_tokens:
                tf = frequency.get(term, 0)
                if not tf:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = tf + self.k1 * (1 - self.b + self.b * length / (self.avg_length or 1))
                score += idf * (tf * (self.k1 + 1)) / denominator
            results.append(score)
        return results

    def top_k(self, query: str, k: int, allowed: set[int] | None = None) -> list[tuple[int, float]]:
        scores = self.scores(query)
        candidates = [
            (index, score)
            for index, score in enumerate(scores)
            if score > 0 and (allowed is None or index in allowed)
        ]
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[:k]
