"""Hybrid RAG package (P2)."""
from .service import (
    RAGError,
    answer_question,
    clear_knowledge,
    get_index,
    index_documents,
    knowledge_status,
    remove_document_from_index,
    reset_index,
    search_knowledge,
)

__all__ = [
    "RAGError",
    "answer_question",
    "clear_knowledge",
    "get_index",
    "index_documents",
    "knowledge_status",
    "remove_document_from_index",
    "reset_index",
    "search_knowledge",
]
