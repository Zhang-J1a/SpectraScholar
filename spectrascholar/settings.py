"""Centralized application configuration.

All runtime knobs live here so that the rest of the code never reaches into
``os.environ`` directly.  Secrets are only ever read from the environment /
``.env`` and are never returned by the API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# Tests set this flag so a developer's real .env (and real API keys) is never
# loaded into the test process.
if os.getenv("SPECTRASCHOLAR_SKIP_DOTENV", "").strip() != "1":
    load_dotenv(ROOT / ".env")

# If the operator supplies only a DeepSeek key, prefer DeepSeek chat models by
# default. If OpenAI is also configured, keep OpenAI defaults for embeddings and
# backwards compatibility. Explicit GPTR_* / EXTRACTION_MODEL / ANSWER_MODEL
# environment variables always win.
_DEEPSEEK_ONLY = bool(os.getenv("DEEPSEEK_API_KEY", "").strip()) and not bool(
    os.getenv("OPENAI_API_KEY", "").strip()
)
_DEFAULT_FAST_LLM = "deepseek:deepseek-chat" if _DEEPSEEK_ONLY else "openai:gpt-4o-mini"
_DEFAULT_SMART_LLM = "deepseek:deepseek-chat" if _DEEPSEEK_ONLY else "openai:gpt-4o"
_DEFAULT_EXTRACTION_MODEL = "deepseek-chat" if _DEEPSEEK_ONLY else "gpt-4o-mini"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return max(minimum, float(raw))
    except ValueError:
        return default


def _env_list(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    workspace: Path = Path(os.getenv("WORKSPACE_DIR", str(ROOT / "workspace"))).resolve()

    # -- application ---------------------------------------------------------
    app_name: str = "SpectraScholar"
    app_version: str = "0.2.0"
    app_env: str = os.getenv("APP_ENV", "local").lower()
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_json: bool = _env_bool("LOG_JSON", False)
    api_key: str = os.getenv("API_KEY", "")
    rate_limit_per_minute: int = _env_int("RATE_LIMIT_PER_MINUTE", 60)
    cors_origins: list[str] = field(default_factory=lambda: _env_list("CORS_ORIGINS"))
    max_concurrent_jobs: int = _env_int("MAX_CONCURRENT_JOBS", 2, 1)

    # -- research (P0) -------------------------------------------------------
    research_backend: str = os.getenv("RESEARCH_BACKEND", "demo").lower()
    research_timeout_seconds: int = _env_int("RESEARCH_TIMEOUT_SECONDS", 900, 5)
    research_phase_timeout_seconds: int = _env_int("RESEARCH_PHASE_TIMEOUT_SECONDS", 600, 5)
    research_max_attempts: int = _env_int("RESEARCH_MAX_ATTEMPTS", 2, 1)
    retry_backoff_seconds: float = _env_float("RETRY_BACKOFF_SECONDS", 2.0)
    gptr_report_type: str = os.getenv("GPTR_REPORT_TYPE", "research_report")
    gptr_retriever: str = os.getenv("GPTR_RETRIEVER", "tavily")
    gptr_max_iterations: int = _env_int("GPTR_MAX_ITERATIONS", 3, 1)
    # GPT Researcher 0.16.x defaults to gpt-5.x; these explicit defaults keep the
    # adapter usable with widely available OpenAI-compatible keys. Override them
    # for other providers (e.g. "ollama:qwen2.5").
    gptr_fast_llm: str = os.getenv("GPTR_FAST_LLM", "").strip() or _DEFAULT_FAST_LLM
    gptr_smart_llm: str = os.getenv("GPTR_SMART_LLM", "").strip() or _DEFAULT_SMART_LLM
    gptr_strategic_llm: str = os.getenv("GPTR_STRATEGIC_LLM", "").strip() or _DEFAULT_SMART_LLM
    gptr_embedding: str = os.getenv("GPTR_EMBEDDING", "")
    gptr_allow_missing_key: bool = _env_bool("GPTR_ALLOW_MISSING_KEY", False)

    # -- extraction (P1) -----------------------------------------------------
    extractor_backend: str = os.getenv("EXTRACTOR_BACKEND", "heuristic").lower()
    extraction_model: str = os.getenv("EXTRACTION_MODEL", "").strip() or _DEFAULT_EXTRACTION_MODEL
    extraction_timeout_seconds: int = _env_int("EXTRACTION_TIMEOUT_SECONDS", 90, 5)
    extraction_max_attempts: int = _env_int("EXTRACTION_MAX_ATTEMPTS", 2, 1)
    extraction_max_candidates: int = _env_int("EXTRACTION_MAX_CANDIDATES", 40, 5)
    table_extraction_enabled: bool = _env_bool("TABLE_EXTRACTION_ENABLED", True)

    # -- uploads / PDF -------------------------------------------------------
    max_upload_mb: int = _env_int("MAX_UPLOAD_MB", 20, 1)
    max_pdf_pages: int = _env_int("MAX_PDF_PAGES", 30, 1)
    max_extract_chars: int = _env_int("MAX_EXTRACT_CHARS", 60000, 1000)
    max_filename_length: int = _env_int("MAX_FILENAME_LENGTH", 160, 16)

    # -- RAG (P2) ------------------------------------------------------------
    embedding_backend: str = os.getenv("EMBEDDING_BACKEND", "hash").lower()
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    embedding_dim: int = _env_int("EMBEDDING_DIM", 512, 64)
    embedding_batch_size: int = _env_int("EMBEDDING_BATCH_SIZE", 32, 1)
    rag_chunk_chars: int = _env_int("RAG_CHUNK_CHARS", 1200, 200)
    rag_chunk_overlap: int = _env_int("RAG_CHUNK_OVERLAP", 180, 0)
    rag_top_k: int = _env_int("RAG_TOP_K", 6, 1)
    rag_max_top_k: int = _env_int("RAG_MAX_TOP_K", 20, 1)
    rag_min_score: float = _env_float("RAG_MIN_SCORE", 0.0)
    rerank_backend: str = os.getenv("RERANK_BACKEND", "lexical").lower()
    answer_backend: str = os.getenv("ANSWER_BACKEND", "extractive").lower()
    answer_model: str = os.getenv("ANSWER_MODEL", "").strip() or _DEFAULT_EXTRACTION_MODEL
    answer_timeout_seconds: int = _env_int("ANSWER_TIMEOUT_SECONDS", 90, 5)

    # -- workflow (P3) -------------------------------------------------------
    workflow_max_retries: int = _env_int("WORKFLOW_MAX_RETRIES", 1, 0)
    workflow_step_timeout_seconds: int = _env_int("WORKFLOW_STEP_TIMEOUT_SECONDS", 600, 5)

    # -- derived paths -------------------------------------------------------
    @property
    def paper_dir(self) -> Path:
        return self.workspace / "papers"

    @property
    def report_dir(self) -> Path:
        return self.workspace / "reports"

    @property
    def kb_dir(self) -> Path:
        return self.workspace / "kb"

    @property
    def config_dir(self) -> Path:
        return self.workspace / "gptr_configs"

    @property
    def db_path(self) -> Path:
        return self.workspace / "spectrascholar.sqlite3"

    @property
    def kb_index_path(self) -> Path:
        return self.kb_dir / "index.json"

    def ensure_directories(self) -> None:
        for path in (self.workspace, self.paper_dir, self.report_dir, self.kb_dir, self.config_dir):
            path.mkdir(parents=True, exist_ok=True)

    def public_summary(self) -> dict[str, object]:
        """Configuration safe to expose to the browser (no secrets)."""
        return {
            "research_backend": self.research_backend,
            "extractor_backend": self.extractor_backend,
            "embedding_backend": self.embedding_backend,
            "answer_backend": self.answer_backend,
            "rerank_backend": self.rerank_backend,
            "research_timeout_seconds": self.research_timeout_seconds,
            "max_upload_mb": self.max_upload_mb,
            "max_pdf_pages": self.max_pdf_pages,
            "rag_top_k": self.rag_top_k,
            "auth_enabled": bool(self.api_key),
            "rate_limit_per_minute": self.rate_limit_per_minute,
        }


settings = Settings()
