from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=1500, description="具体研究问题")
    source: Literal["web", "local"] = "web"
    domain: Literal["hyperspectral", "general"] = "hyperspectral"
    language: Literal["zh", "en"] = "zh"

    @field_validator("topic")
    @classmethod
    def no_blank_topic(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("研究主题不能是空白")
        return value.strip()


class JobSubmitted(BaseModel):
    job_id: str
    status: str


class JobDetails(BaseModel):
    job_id: str
    topic: str
    source: str
    domain: str
    status: str
    error: str | None = None
    report: str | None = None
    created_at: str
    finished_at: str | None = None


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    size: int


class CompareRequest(BaseModel):
    document_ids: list[str] = Field(min_length=2, max_length=5)

    @field_validator("document_ids")
    @classmethod
    def unique_docs(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("请不要选择重复论文")
        return value


class Evidence(BaseModel):
    value: str = ""
    page: int = Field(ge=1)
    quote: str = ""
    verified: bool = False


class MetricEvidence(BaseModel):
    dataset: str = ""
    metric: str = ""  # OA / AA / Kappa / other
    value: str = ""
    page: int = Field(ge=1)
    quote: str = ""
    verified: bool = False


class PaperExtraction(BaseModel):
    document_id: str
    filename: str
    method: list[Evidence] = Field(default_factory=list)
    datasets: list[Evidence] = Field(default_factory=list)
    metrics: list[MetricEvidence] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ComparisonResponse(BaseModel):
    papers: list[PaperExtraction]
    extraction_mode: str
    disclaimer: str = "只保留与原文页码片段匹配的证据；仍需人工核对表格及实验设置。"
