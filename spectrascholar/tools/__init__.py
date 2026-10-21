"""Tool layer for the SpectraScholar research agent."""
from .arxiv_search import ArxivSearchError, search_arxiv

__all__ = ["ArxivSearchError", "search_arxiv"]
