"""arXiv search tool with year/task filtering, DOI dedup and retries.

This is a real callable tool for the agent layer, not a prompt-only feature.
The FastAPI endpoint is a thin adapter; tests inject a fake client and never
touch the network.
"""
from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any

from ..settings import settings

try:
    import arxiv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - dependency is in requirements
    arxiv = None


class ArxivSearchError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = value.strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    return doi.lower() or None


def _short_id(result: Any) -> str:
    raw = result.get_short_id() if hasattr(result, "get_short_id") else str(result.entry_id)
    return re.sub(r"v\d+$", "", str(raw))


_STOPWORDS = {
    "a",
    "an",
    "and",
    "based",
    "for",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
}


def _keyword_query(query: str) -> str:
    """Turn plain keywords into arXiv all-field terms.

    A raw ``hyperspectral graph neural network`` query is treated as a loose
    relevance query by arXiv and can return unrelated recent papers. Explicit
    field syntax (``all:``, ``ti:``, ``AND``/``OR``) is passed through.
    """
    text = query.strip()
    if ":" in text or re.search(r"\b(?:AND|OR)\b", text):
        return text
    terms: list[str] = []
    for phrase, word in re.findall(r'"([^"]+)"|(\S+)', text):
        term = (phrase or word).strip()
        if not term or term.casefold() in _STOPWORDS:
            continue
        if phrase:
            terms.append(f'all:"{phrase.replace(chr(34), " ")}"')
        else:
            terms.append(f"all:{term}")
    return " AND ".join(terms) or text


def _build_query(
    query: str,
    year_from: int | None,
    year_to: int | None,
    task_topic: str | None,
) -> str:
    parts = [_keyword_query(query)]
    if year_from or year_to:
        start = f"{year_from or 1900}01010000"
        end = f"{year_to or datetime.now(UTC).year}12312359"
        parts.append(f"submittedDate:[{start} TO {end}]")
    if task_topic and task_topic.strip():
        parts.append(_keyword_query(task_topic))
    return " AND ".join(part for part in parts if part)


def _paper_from_result(result: Any, task_topic: str | None) -> dict[str, Any]:
    published = getattr(result, "published", None)
    published_text = published.isoformat() if hasattr(published, "isoformat") else str(published or "")
    year = getattr(published, "year", None)
    title = str(getattr(result, "title", "") or "").replace("\n", " ").strip()
    abstract = str(getattr(result, "summary", "") or "").replace("\n", " ").strip()
    topic_match = False
    if task_topic:
        haystack = f"{title} {abstract}".casefold()
        topic_match = all(
            token.casefold() in haystack
            for token in task_topic.split()
            if len(token) >= 2
        )
    return {
        "arxiv_id": _short_id(result),
        "title": title,
        "authors": [str(author) for author in getattr(result, "authors", [])],
        "published": published_text,
        "year": year,
        "doi": _clean_doi(getattr(result, "doi", None)),
        "abstract": abstract,
        "pdf_url": str(getattr(result, "pdf_url", "") or "") or None,
        "entry_url": str(getattr(result, "entry_id", "") or ""),
        "categories": [str(category) for category in getattr(result, "categories", [])],
        "primary_category": str(getattr(result, "primary_category", "") or "") or None,
        "journal_ref": str(getattr(result, "journal_ref", "") or "") or None,
        "task_topic_match": topic_match,
    }


def _paper_key(paper: dict[str, Any]) -> tuple[str, str]:
    if paper["doi"]:
        return ("doi", paper["doi"])
    if paper["arxiv_id"]:
        return ("arxiv", paper["arxiv_id"])
    return ("title", " ".join(paper["title"].casefold().split()))


def search_arxiv(
    query: str,
    *,
    year_from: int | None = None,
    year_to: int | None = None,
    task_topic: str | None = None,
    start: int = 0,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search arXiv. Returns a JSON-serializable payload for the API adapter."""
    if arxiv is None:  # pragma: no cover
        raise ArxivSearchError("arxiv_unavailable", "未安装 arxiv 包")
    if not query.strip():
        raise ArxivSearchError("invalid_query", "query 不能为空")

    max_results = max(1, min(max_results, settings.arxiv_max_results))
    start = max(0, start)
    effective_query = _build_query(query, year_from, year_to, task_topic)
    fetch_count = min(200, start + max_results + 1)
    search = arxiv.Search(
        query=effective_query,
        max_results=fetch_count,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(
        page_size=min(100, fetch_count),
        delay_seconds=3.0,
        num_retries=settings.arxiv_max_attempts,
    )

    attempts = 0
    raw: list[Any] = []
    for attempt in range(1, settings.arxiv_max_attempts + 1):
        attempts = attempt
        try:
            raw = list(client.results(search))
            break
        except Exception as exc:  # network/provider errors are retryable here
            if attempt >= settings.arxiv_max_attempts:
                raise ArxivSearchError(
                    "arxiv_unavailable",
                    f"arXiv 请求失败: {type(exc).__name__}: {str(exc)[:300]}",
                    retryable=True,
                ) from exc
            time.sleep(1.5 * attempt)

    papers = [_paper_from_result(result, task_topic) for result in raw[start : start + max_results]]
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for paper in papers:
        key = _paper_key(paper)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(paper)

    return {
        "tool": "arxiv_search",
        "query": query,
        "effective_query": effective_query,
        "year_from": year_from,
        "year_to": year_to,
        "task_topic": task_topic,
        "start": start,
        "max_results": max_results,
        "returned": len(deduped),
        "has_more": len(raw) > start + max_results,
        "duplicates_filtered": duplicates,
        "attempts": attempts,
        "provider": "arxiv",
        "papers": deduped,
    }
