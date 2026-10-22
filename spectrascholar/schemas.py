"""Pydantic contracts shared by the API, the agent pipeline and the tests.

Design rule: every extracted scientific value is attached to an
:class:`EvidenceRef`.  A value without a successful quote check is never
returned as a verified extraction.  The data model deliberately separates:

* ``quote_found``      – the characters exist on the PDF page;
* ``value_supported``  – the submitted value occurs inside that quote;
* ``semantic_checked`` – a human/model checked that the sentence really means
  what the extraction claims (this project does **not** automate that).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
ExtractionMode = Literal["heuristic", "llm"]
EvidenceStatus = Literal[
    "verified_quote",              # quote on page AND value inside quote
    "verified_page_only",          # citation points at an existing page, no quote check
    "quote_found_value_mismatch",  # quote exists, but the claimed value is not in it
    "quote_not_found",             # quote does not occur on that page
    "page_missing",                # page number outside the PDF
    "document_missing",            # document id is unknown
    "external_unchecked",          # web link, no network verification performed
    "local_file_unverified",       # relative PDF filename, no page/document ID
    "malformed",                   # citation syntax could not be parsed
    "unverified",                  # extraction not checked at all
]
VerificationLevel = Literal["quote", "page", "none"]
WorkflowStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]


# ---------------------------------------------------------------------------
# Research jobs
# ---------------------------------------------------------------------------
class ResearchRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=1500, description="具体研究问题")
    source: Literal["web", "local"] = "web"
    domain: Literal["hyperspectral", "general"] = "hyperspectral"
    language: Literal["zh", "en"] = "zh"
    max_elapsed_seconds: int | None = Field(default=None, ge=30, le=7200)
    max_cost_usd: float | None = Field(default=None, ge=0.0, le=100.0)

    @field_validator("topic")
    @classmethod
    def no_blank_topic(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("研究主题不能是空白")
        return value


class JobSubmitted(BaseModel):
    job_id: str
    status: JobStatus
    trace_id: str
    backend: str
    is_demo: bool


class JobEvent(BaseModel):
    event_id: int
    job_id: str
    level: str
    step: str
    message: str
    duration_ms: int | None = None
    created_at: str


class JobSummary(BaseModel):
    """Task-list projection without the (potentially large) report body."""

    job_id: str
    topic: str
    source: str
    domain: str
    language: str = "zh"
    status: JobStatus
    backend: str = "demo"
    is_demo: bool = True
    error: str | None = None
    error_type: str | None = None
    trace_id: str | None = None
    attempts: int = 0
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_ms: int | None = None
    max_elapsed_seconds: int | None = None
    max_cost_usd: float | None = None
    cancel_requested: bool = False


class JobDetails(JobSummary):
    report: str | None = None
    citation_audit: dict | None = None
    metadata: dict | None = None


# ---------------------------------------------------------------------------
# Documents / PDF pages
# ---------------------------------------------------------------------------
class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    size: int
    sha256: str | None = None
    page_count: int | None = None
    title: str | None = None
    created_at: str | None = None


class PageText(BaseModel):
    page: int
    text: str
    char_count: int


class DocumentPages(BaseModel):
    document_id: str
    filename: str
    page_count: int
    pages: list[PageText]


# ---------------------------------------------------------------------------
# Evidence primitives (legacy + new)
# ---------------------------------------------------------------------------
class Evidence(BaseModel):
    """Legacy flat evidence record kept for backward-compatible scripts."""

    value: str = ""
    page: int = Field(ge=1)
    quote: str = ""
    verified: bool = False


class MetricEvidence(BaseModel):
    """Legacy flat metric record kept for backward-compatible scripts."""

    dataset: str = ""
    metric: str = ""
    value: str = ""
    page: int = Field(ge=1)
    quote: str = ""
    verified: bool = False


class EvidenceRef(BaseModel):
    document_id: str
    page: int | None = None
    quote: str | None = None
    value: str | None = None
    status: EvidenceStatus = "unverified"
    verification: VerificationLevel = "none"
    semantic_checked: bool = False
    note: str | None = None

    @property
    def accepted(self) -> bool:
        return self.status == "verified_quote"


class ExtractedField(BaseModel):
    value: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    method: ExtractionMode = "heuristic"
    confidence: Literal["high", "medium", "low"] = "medium"
    note: str | None = None

    @property
    def missing(self) -> bool:
        return self.value is None or not self.value.strip()


class RejectionRecord(BaseModel):
    field: str
    value: str | None = None
    page: int | None = None
    reason: str
    note: str | None = None


class ExtractionStats(BaseModel):
    pages_scanned: int = 0
    characters_scanned: int = 0
    candidates: int = 0
    accepted: int = 0
    rejected: int = 0
    elapsed_ms: int = 0


# ---------------------------------------------------------------------------
# Structured paper extraction (P1-A)
# ---------------------------------------------------------------------------
class PaperMetadata(BaseModel):
    title: ExtractedField = Field(default_factory=ExtractedField)
    authors: ExtractedField = Field(default_factory=ExtractedField)
    year: ExtractedField = Field(default_factory=ExtractedField)
    venue: ExtractedField = Field(default_factory=ExtractedField)


class MethodRecord(BaseModel):
    name: str
    family: str | None = None  # CNN / Transformer / GNN / other / unspecified
    graph_construction: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    note: str | None = None


class DatasetRecord(BaseModel):
    name: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class GraphConstructionRecord(BaseModel):
    kind: str  # KNN / RBF / static / dynamic / superpixel / other
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ExperimentCondition(BaseModel):
    dataset: str | None = None
    train_ratio: str | None = None
    patch_size: str | None = None
    protocol: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    note: str | None = None


class MetricRecord(BaseModel):
    dataset: str | None = None
    method: str | None = None
    metric: str  # OA / AA / Kappa / other
    value: str
    train_ratio: str | None = None
    patch_size: str | None = None
    protocol: str | None = None
    source: Literal["text", "table", "llm"] = "text"
    evidence: list[EvidenceRef] = Field(default_factory=list)
    note: str | None = None


class PaperExtraction(BaseModel):
    document_id: str
    filename: str
    extraction_mode: ExtractionMode = "heuristic"
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    methods: list[MethodRecord] = Field(default_factory=list)
    datasets: list[DatasetRecord] = Field(default_factory=list)
    graph_constructions: list[GraphConstructionRecord] = Field(default_factory=list)
    experiment_conditions: list[ExperimentCondition] = Field(default_factory=list)
    metrics: list[MetricRecord] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    rejections: list[RejectionRecord] = Field(default_factory=list)
    stats: ExtractionStats = Field(default_factory=ExtractionStats)

    @property
    def has_text(self) -> bool:
        return bool(self.methods or self.datasets or self.metrics)


# ---------------------------------------------------------------------------
# Comparison (P1-B)
# ---------------------------------------------------------------------------
class CompareRequest(BaseModel):
    document_ids: list[str] = Field(min_length=2, max_length=5)
    mode: Literal["auto", "heuristic", "llm"] = "auto"
    language: Literal["zh", "en"] = "zh"

    @field_validator("document_ids")
    @classmethod
    def unique_docs(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("请不要选择重复论文")
        return value


class MethodRow(BaseModel):
    document_id: str
    filename: str
    method: str
    family: str | None = None
    graph_construction: list[str] = Field(default_factory=list)
    evidence_status: str = "unverified"


class DatasetCell(BaseModel):
    document_id: str
    present: bool
    pages: list[int] = Field(default_factory=list)


class DatasetRow(BaseModel):
    dataset: str
    cells: list[DatasetCell] = Field(default_factory=list)


class MetricRow(BaseModel):
    document_id: str
    filename: str
    method: str | None = None
    dataset: str | None = None
    metric: str
    value: str
    train_ratio: str | None = None
    patch_size: str | None = None
    protocol: str | None = None
    source: Literal["text", "table", "llm"] = "text"
    evidence_status: str = "unverified"
    comparable_group: str | None = None
    comparable: bool = False
    rank_in_group: int | None = None
    reason: str | None = None


class ComparabilityIssue(BaseModel):
    code: str
    message: str
    document_ids: list[str] = Field(default_factory=list)
    dataset: str | None = None
    metric: str | None = None


class PaperProfile(BaseModel):
    document_id: str
    filename: str
    title: str | None = None
    authors: str | None = None
    year: str | None = None
    methods: list[str] = Field(default_factory=list)
    model_families: list[str] = Field(default_factory=list)
    datasets: list[str] = Field(default_factory=list)
    metrics_summary: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    applicable_scenarios: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    comparison_id: str
    papers: list[PaperExtraction]
    profiles: list[PaperProfile] = Field(default_factory=list)
    method_rows: list[MethodRow] = Field(default_factory=list)
    dataset_matrix: list[DatasetRow] = Field(default_factory=list)
    metric_rows: list[MetricRow] = Field(default_factory=list)
    comparability_issues: list[ComparabilityIssue] = Field(default_factory=list)
    extraction_mode: str
    generated_at: str
    markdown: str
    disclaimer: str = (
        "证据核验只证明引文出现在指定 PDF 页码，不代表事实语义正确，也不代表不同实验设置下的"
        "指标可以直接排名。训练比例或协议缺失的数值一律标记为不可比。"
    )


# ---------------------------------------------------------------------------
# Citation auditing (P1-C)
# ---------------------------------------------------------------------------
class CitationCheck(BaseModel):
    raw: str
    kind: Literal["local_pdf", "local_file", "external_url", "unknown"] = "unknown"
    document_id: str | None = None
    filename: str | None = None
    page: int | None = None
    quote: str | None = None
    status: EvidenceStatus = "unverified"
    semantic_checked: bool = False
    message: str = ""


class UnsupportedClaim(BaseModel):
    sentence: str
    reason: str


class ClaimCheck(BaseModel):
    """One report sentence and the best citation evidence found for it."""

    sentence: str
    citation: str | None = None
    kind: Literal["local_pdf", "external_url", "none"] = "none"
    status: Literal[
        "supported_quote",
        "page_only",
        "external_unchecked",
        "no_citation",
        "citation_failed",
    ] = "no_citation"
    document_id: str | None = None
    filename: str | None = None
    page: int | None = None
    quote: str | None = None
    reason: str = ""


class CitationAudit(BaseModel):
    total: int = 0
    verified_local: int = 0
    page_only_local: int = 0
    failed_local: int = 0
    external_unchecked: int = 0
    local_file_unverified: int = 0
    unsupported_claims: list[UnsupportedClaim] = Field(default_factory=list)
    claims: list[ClaimCheck] = Field(default_factory=list)
    claims_supported: int = 0
    claims_page_only: int = 0
    claims_external_unchecked: int = 0
    claims_no_citation: int = 0
    claims_failed: int = 0
    checks: list[CitationCheck] = Field(default_factory=list)
    checked_at: str = ""
    scope_note: str = (
        "本报告只核验引文是否存在于指定 PDF 页码，并检查数值性结论是否有引用；"
        "不验证事实语义、论文质量或实验可比性。外部 URL 未联网核验；"
        "相对 PDF 文件名链接缺少页码/文档 ID，只能标记为未做页级核验。"
    )


class VerifyEvidenceRequest(BaseModel):
    document_id: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=4000)
    value: str | None = Field(default=None, max_length=200)


# ---------------------------------------------------------------------------
# RAG knowledge base (P2)
# ---------------------------------------------------------------------------
class IndexRequest(BaseModel):
    document_ids: list[str] | None = None


class IndexedDocument(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunks: int


class SkippedDocument(BaseModel):
    document_id: str
    filename: str
    reason: str


class IndexResponse(BaseModel):
    indexed_documents: list[IndexedDocument]
    skipped: list[SkippedDocument]
    total_chunks: int
    embedding_backend: str
    elapsed_ms: int
    notes: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    top_k: int = Field(default=6, ge=1, le=20)
    document_ids: list[str] | None = None
    mode: Literal["hybrid", "vector", "bm25", "auto"] = "hybrid"

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("检索问题不能为空")
        return value


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page: int
    text: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    citation: str


class SearchResponse(BaseModel):
    query: str
    mode: str
    embedding_backend: str
    hits: list[SearchHit]
    elapsed_ms: int
    note: str = ""


class AnswerRequest(SearchRequest):
    require_citations: bool = True


class AnswerResponse(BaseModel):
    query: str
    answer: str
    grounded: bool
    refusal: bool
    citations: list[CitationCheck]
    hits: list[SearchHit]
    answer_mode: str
    embedding_backend: str
    elapsed_ms: int
    note: str = ""


# ---------------------------------------------------------------------------
# Workflow (P3)
# ---------------------------------------------------------------------------
class WorkflowRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=1000)
    document_ids: list[str] = Field(min_length=2, max_length=5)
    extraction_mode: Literal["auto", "heuristic", "llm"] = "auto"
    language: Literal["zh", "en"] = "zh"
    idempotency_key: str | None = Field(default=None, max_length=120)
    # Tool calling is opt-in; the local PDF pipeline remains unchanged by default.
    tools: list[Literal["arxiv_search"]] = Field(default_factory=list, max_length=1)
    arxiv_year_from: int | None = Field(default=None, ge=1900, le=2100)
    arxiv_year_to: int | None = Field(default=None, ge=1900, le=2100)
    arxiv_max_results: int = Field(default=5, ge=1, le=20)

    @field_validator("document_ids")
    @classmethod
    def unique_docs(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("请不要选择重复论文")
        return value


class WorkflowStep(BaseModel):
    name: str
    status: StepStatus
    attempt: int = 0
    input_summary: str | None = None
    output_summary: str | None = None
    error: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None


class WorkflowSubmitted(BaseModel):
    workflow_id: str
    status: WorkflowStatus
    trace_id: str


class WorkflowDetails(BaseModel):
    workflow_id: str
    topic: str
    document_ids: list[str]
    extraction_mode: str
    language: str
    status: WorkflowStatus
    current_step: str | None = None
    steps: list[WorkflowStep] = Field(default_factory=list)
    comparison_id: str | None = None
    report: str | None = None
    citation_audit: dict | None = None
    error: str | None = None
    trace_id: str | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_ms: int | None = None


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    app_version: str
    research_backend: str
    extractor_backend: str
    embedding_backend: str
    answer_backend: str
    auth_enabled: bool
    demo_mode: bool
    knowledge_chunks: int = 0
    documents: int = 0


# ---------------------------------------------------------------------------
# Tool calling (V2.1)
# ---------------------------------------------------------------------------
class ArxivPaper(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    published: str
    year: int | None = None
    doi: str | None = None
    abstract: str = ""
    pdf_url: str | None = None
    entry_url: str
    categories: list[str] = Field(default_factory=list)
    primary_category: str | None = None
    journal_ref: str | None = None
    task_topic_match: bool = False


class AgentLoopRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    max_steps: int = Field(default=3, ge=1, le=5)
    allowed_tools: list[Literal["arxiv_search", "local_search"]] = Field(
        default_factory=lambda: ["arxiv_search", "local_search"],
        max_length=2,
    )


class AgentLoopResponse(BaseModel):
    query: str
    answer: str
    stopped_reason: str
    steps: int
    observations: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class ArxivSearchResponse(BaseModel):
    tool: Literal["arxiv_search"] = "arxiv_search"
    query: str
    effective_query: str
    year_from: int | None = None
    year_to: int | None = None
    task_topic: str | None = None
    start: int = 0
    max_results: int
    returned: int
    has_more: bool = False
    duplicates_filtered: int = 0
    attempts: int = 1
    provider: str = "arxiv"
    papers: list[ArxivPaper] = Field(default_factory=list)
