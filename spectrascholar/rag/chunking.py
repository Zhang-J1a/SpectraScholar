"""Page-aware text chunking.

Every chunk keeps the page number and character offsets so an answer can be
traced back to a PDF page.  Chunks never cross page boundaries.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_SENTENCE_RE = re.compile(r"[^.!?。！？\n]+[.!?。！？]?")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    page: int
    text: str
    start: int
    end: int


def _unit_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _SENTENCE_RE.finditer(text):
        if match.group(0).strip():
            spans.append((match.start(), match.end()))
    if not spans:
        spans = [(0, len(text))]
    return spans


def _hard_split(text: str, start: int, end: int, max_chars: int) -> list[tuple[int, int]]:
    return [(pos, min(pos + max_chars, end)) for pos in range(start, end, max_chars)]


def chunk_page(
    document_id: str,
    page: int,
    text: str,
    *,
    max_chars: int = 1200,
    overlap: int = 180,
) -> list[Chunk]:
    if not text or not text.strip():
        return []
    max_chars = max(200, max_chars)
    overlap = max(0, min(overlap, max_chars // 2))
    units = _unit_spans(text)
    chunks: list[Chunk] = []
    cursor = 0
    while cursor < len(units):
        start = units[cursor][0]
        end = units[cursor][1]
        next_index = cursor + 1
        while next_index < len(units) and units[next_index][1] - start <= max_chars:
            end = units[next_index][1]
            next_index += 1
        if end - start > max_chars:
            for hard_start, hard_end in _hard_split(text, start, end, max_chars):
                piece = text[hard_start:hard_end].strip()
                if len(piece) >= 20:
                    digest = hashlib.sha1(
                        f"{document_id}:{page}:{hard_start}:{hard_end}".encode()
                    ).hexdigest()[:16]
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document_id[:8]}-p{page}-{digest}",
                            document_id=document_id,
                            page=page,
                            text=piece,
                            start=hard_start,
                            end=hard_end,
                        )
                    )
            next_index = max(next_index, cursor + 1)
        else:
            piece = text[start:end].strip()
            if len(piece) >= 20:
                digest = hashlib.sha1(f"{document_id}:{page}:{start}:{end}".encode()).hexdigest()[:16]
                chunks.append(
                    Chunk(
                        chunk_id=f"{document_id[:8]}-p{page}-{digest}",
                        document_id=document_id,
                        page=page,
                        text=piece,
                        start=start,
                        end=end,
                    )
                )
        if next_index >= len(units):
            break
        # Step back far enough to include an overlap, but always move forward.
        overlap_start = max(0, end - overlap)
        new_cursor = next_index
        while new_cursor > cursor and units[new_cursor - 1][1] > overlap_start:
            new_cursor -= 1
        cursor = max(new_cursor, cursor + 1)
    return chunks


def chunk_pages(
    document_id: str,
    pages: list[str],
    *,
    max_chars: int = 1200,
    overlap: int = 180,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page_number, text in enumerate(pages, 1):
        chunks.extend(
            chunk_page(
                document_id,
                page_number,
                text,
                max_chars=max_chars,
                overlap=overlap,
            )
        )
    return chunks
