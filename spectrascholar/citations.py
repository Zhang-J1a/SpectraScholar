"""Citation parsing and verification (P1-C).

Supported local citation syntax (used by our own reports and RAG answers)::

    [[doc:<document_id> p.<page>]]
    [[doc:<document_id> p.<page> "exact quote from that page"]]

External Markdown links are counted but **never** fetched automatically; they
are reported as ``external_unchecked``.  The audit also finds numeric
experimental claims that have no citation at all.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime

from .evidence import make_evidence_ref, normalized
from .schemas import CitationAudit, CitationCheck, UnsupportedClaim

LOCAL_RE = re.compile(
    r"\[\[\s*doc:([A-Za-z0-9_-]+)\s+p\.?\s*(\d+)(?:\s+\"([^\"]{1,1200})\")?\s*\]\]",
    re.IGNORECASE,
)
LOCAL_PREFIX_RE = re.compile(r"\[\[\s*doc:", re.IGNORECASE)
EXTERNAL_LINK_RE = re.compile(r"(?<!!)\[([^\]]{0,200})\]\((https?://[^\s)]+)\)", re.IGNORECASE)
BARE_URL_RE = re.compile(r"(?<!\()(https?://[^\s<>\]]+)", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

Resolver = Callable[[str], tuple[dict | None, list[str] | None]]

METRIC_CLAIM_RE = re.compile(
    r"(?:\bOA\b|\bAA\b|\bKappa\b|\bIoU\b|\bmIoU\b|overall\s+accuracy|average\s+accuracy|"
    r"accuracy|precision|recall|F1|准确率|精度|总体精度|平均精度)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*%?")


def _sanitize_for_claim(sentence: str) -> str:
    return LOCAL_RE.sub(" ", sentence)


def _iter_sentences(report: str) -> list[str]:
    cleaned = CODE_FENCE_RE.sub("\n", report)
    sentences: list[str] = []
    for block in cleaned.splitlines():
        line = block.strip()
        if not line:
            continue
        if line.startswith(("#", "|", "```", "---")):
            continue
        if line.startswith(("-", "*", ">")) and len(line) < 40:
            continue
        # Split on English/Chinese sentence terminators, keeping the text.
        parts = re.split(r"(?<=[。！？!?;；])\s*|(?<=\.)\s+(?=[A-Z0-9\u4e00-\u9fff])", line)
        sentences.extend(part.strip() for part in parts if part.strip())
    return sentences


def find_unsupported_claims(report: str, *, limit: int = 50) -> list[UnsupportedClaim]:
    claims: list[UnsupportedClaim] = []
    seen: set[str] = set()
    for sentence in _iter_sentences(report):
        if not METRIC_CLAIM_RE.search(sentence) or not NUMBER_RE.search(sentence):
            continue
        if LOCAL_RE.search(sentence) or EXTERNAL_LINK_RE.search(sentence):
            continue
        key = normalized(sentence)[:300]
        if key in seen:
            continue
        seen.add(key)
        claims.append(
            UnsupportedClaim(
                sentence=sentence[:500],
                reason="包含实验指标数值，但同一句中没有本地 PDF 引用或外部链接",
            )
        )
        if len(claims) >= limit:
            break
    return claims


def audit_report(
    report: str,
    resolver: Resolver,
    *,
    skip_claims: bool = False,
) -> CitationAudit:
    """Verify local citations and flag numerically unsupported claims.

    ``resolver(document_id)`` must return ``(document_row, pages)``.  A missing
    document returns ``(None, None)``.
    """
    checks: list[CitationCheck] = []
    seen_local: set[tuple[str, int, str | None]] = set()
    local_spans: list[tuple[int, int]] = []

    for match in LOCAL_RE.finditer(report):
        local_spans.append((match.start(), match.end()))
        document_id, page_raw, quote = match.group(1), match.group(2), match.group(3)
        page = int(page_raw)
        key = (document_id, page, quote)
        if key in seen_local:
            continue
        seen_local.add(key)
        raw = match.group(0)
        document, pages = resolver(document_id)
        if document is None:
            checks.append(
                CitationCheck(
                    raw=raw,
                    kind="local_pdf",
                    document_id=document_id,
                    page=page,
                    quote=quote,
                    status="document_missing",
                    message="引用的文档不存在",
                )
            )
            continue
        filename = document.get("filename")
        if pages is None:
            checks.append(
                CitationCheck(
                    raw=raw,
                    kind="local_pdf",
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    quote=quote,
                    status="page_missing",
                    message="PDF 文件缺失或无法读取",
                )
            )
            continue
        if not 1 <= page <= len(pages):
            checks.append(
                CitationCheck(
                    raw=raw,
                    kind="local_pdf",
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    quote=quote,
                    status="page_missing",
                    message=f"页码超出范围（共 {len(pages)} 页）",
                )
            )
            continue
        if quote:
            evidence = make_evidence_ref(document_id, pages, page, quote)
            checks.append(
                CitationCheck(
                    raw=raw,
                    kind="local_pdf",
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    quote=quote,
                    status=evidence.status,
                    message=evidence.note or ("原文片段匹配成功" if evidence.accepted else "原文片段未匹配"),
                )
            )
        else:
            checks.append(
                CitationCheck(
                    raw=raw,
                    kind="local_pdf",
                    document_id=document_id,
                    filename=filename,
                    page=page,
                    status="verified_page_only",
                    message="页码存在；未提供原文片段，因此只完成页码级核验",
                )
            )

    for match in EXTERNAL_LINK_RE.finditer(report):
        checks.append(
            CitationCheck(
                raw=match.group(0),
                kind="external_url",
                status="external_unchecked",
                message="外部链接；本次运行未联网核验可用性或内容",
            )
        )

    for match in LOCAL_PREFIX_RE.finditer(report):
        # Report a malformed local marker only if it is not covered by LOCAL_RE.
        covered = any(start <= match.start() < end for start, end in local_spans)
        if not covered:
            checks.append(
                CitationCheck(
                    raw=report[match.start() : match.start() + 120],
                    kind="unknown",
                    status="malformed",
                    message="本地引用语法不完整，应为 [[doc:<id> p.<页码>]]",
                )
            )

    verified_local = sum(1 for check in checks if check.status == "verified_quote")
    page_only = sum(1 for check in checks if check.status == "verified_page_only")
    external = sum(1 for check in checks if check.kind == "external_url")
    failed = sum(
        1
        for check in checks
        if check.kind == "local_pdf" and check.status not in {"verified_quote", "verified_page_only"}
    )
    unsupported = [] if skip_claims else find_unsupported_claims(report)

    return CitationAudit(
        total=len(checks),
        verified_local=verified_local,
        page_only_local=page_only,
        failed_local=failed,
        external_unchecked=external,
        unsupported_claims=unsupported,
        checks=checks,
        checked_at=datetime.now(UTC).isoformat(timespec="seconds"),
        scope_note=(
            "本报告只核验引文是否存在于指定 PDF 页码，并检查数值性结论是否有引用；"
            "不验证事实语义、论文质量或实验可比性。外部 URL 未联网核验。"
        ),
    )


def render_audit_markdown(audit: CitationAudit) -> str:
    lines = [
        "## 引用核验报告（自动生成）",
        "",
        f"- 本地 PDF 引用：{audit.total - audit.external_unchecked} 条；"
        f"原文片段核验通过 {audit.verified_local} 条；仅页码核验 {audit.page_only_local} 条；"
        f"失败 {audit.failed_local} 条。",
        f"- 外部链接：{audit.external_unchecked} 条（未联网核验）。",
        f"- 缺少引用的数值性结论：{len(audit.unsupported_claims)} 条。",
        "",
    ]
    failed = [
        check
        for check in audit.checks
        if check.kind == "local_pdf" and check.status not in {"verified_quote", "verified_page_only"}
    ]
    if failed:
        lines += ["### 未通过的本地引用", "", "| 引用 | 状态 | 说明 |", "|---|---|---|"]
        for check in failed[:30]:
            raw = check.raw.replace("|", "\\|")[:160]
            lines.append(f"| `{raw}` | {check.status} | {check.message} |")
        lines.append("")
    if audit.unsupported_claims:
        lines += ["### 缺少引用的数值性结论（最多 10 条）", ""]
        for claim in audit.unsupported_claims[:10]:
            lines.append(f"- {claim.sentence}")
        lines.append("")
    lines += [
        "> 核验边界：原文出现 ≠ 事实正确 ≠ 实验可比。页码与片段匹配只证明引用可追溯，"
        "不代表语义验证；外部链接未联网核验。",
        "",
    ]
    return "\n".join(lines)


def append_audit_section(report: str, audit: CitationAudit) -> str:
    if "## 引用核验报告（自动生成）" in report:
        return report
    return report.rstrip() + "\n\n" + render_audit_markdown(audit)
