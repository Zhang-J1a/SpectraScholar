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
from .schemas import CitationAudit, CitationCheck, ClaimCheck, UnsupportedClaim

LOCAL_RE = re.compile(
    r"\[\[\s*doc:([A-Za-z0-9_-]+)\s+p\.?\s*(\d+)(?:\s+\"([^\"]{1,1200})\")?\s*\]\]",
    re.IGNORECASE,
)
LOCAL_PREFIX_RE = re.compile(r"\[\[\s*doc:", re.IGNORECASE)
EXTERNAL_LINK_RE = re.compile(r"(?<!!)\[([^\]]{0,200})\]\((https?://[^\s)]+)\)", re.IGNORECASE)
# Upstream GPT Researcher reports often cite local PDFs as relative Markdown
# links, e.g. [hybridsn.pdf](hybridsn.pdf). They are references, but without a
# page number/document id they cannot be page-verified.
LOCAL_FILE_LINK_RE = re.compile(
    r"(?<!!)\[([^\]]{0,200})\]\((?!https?://)([^)\s]+\.pdf(?:#[^)]*)?)\)",
    re.IGNORECASE,
)
BARE_URL_RE = re.compile(r"(?<!\()(https?://[^\s<>\]]+)", re.IGNORECASE)
CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

Resolver = Callable[[str], tuple[dict | None, list[str] | None]]

METRIC_CLAIM_RE = re.compile(
    r"(?:\bOA\b|\bAA\b|\bKappa\b|\bIoU\b|\bmIoU\b|overall\s+accuracy|average\s+accuracy|"
    r"accuracy|precision|recall|F1|准确率|精度|总体精度|平均精度)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*%?")
CLAIM_SIGNAL_RE = re.compile(
    r"(?:\d|\bOA\b|\bAA\b|\bKappa\b|accuracy|outperform|better|worse|"
    r"state-of-the-art|SOTA|superior|improve|reduce|because|therefore|"
    r"优于|低于|高于|提升|下降|达到|表明|因此|因为|最好|最差|相比)",
    re.IGNORECASE,
)


def _claim_from_local(
    sentence: str,
    match: re.Match[str],
    resolver: Resolver,
) -> ClaimCheck:
    document_id, page_raw, quote = match.group(1), match.group(2), match.group(3)
    page = int(page_raw)
    document, pages = resolver(document_id)
    if document is None:
        return ClaimCheck(
            sentence=sentence[:500],
            citation=match.group(0),
            kind="local_pdf",
            status="citation_failed",
            document_id=document_id,
            page=page,
            quote=quote,
            reason="引用的文档不存在",
        )
    filename = document.get("filename")
    if pages is None or not 1 <= page <= len(pages):
        return ClaimCheck(
            sentence=sentence[:500],
            citation=match.group(0),
            kind="local_pdf",
            status="citation_failed",
            document_id=document_id,
            filename=filename,
            page=page,
            quote=quote,
            reason="页码不存在或 PDF 无法读取",
        )
    if not quote:
        return ClaimCheck(
            sentence=sentence[:500],
            citation=match.group(0),
            kind="local_pdf",
            status="page_only",
            document_id=document_id,
            filename=filename,
            page=page,
            reason="只有页码，没有原文片段；不能证明句子被该页支持",
        )
    evidence = make_evidence_ref(document_id, pages, page, quote)
    if evidence.accepted:
        status = "supported_quote"
        reason = "引文在指定页逐字存在"
    else:
        status = "citation_failed"
        reason = evidence.note or "引文未在指定页找到"
    return ClaimCheck(
        sentence=sentence[:500],
        citation=match.group(0),
        kind="local_pdf",
        status=status,
        document_id=document_id,
        filename=filename,
        page=page,
        quote=quote,
        reason=reason,
    )


def audit_claims(report: str, resolver: Resolver, *, limit: int = 100) -> list[ClaimCheck]:
    """Return one citation status per substantive report sentence.

    This is deterministic claim-to-citation mapping, not semantic entailment:
    a verified quote means the quoted text exists; it does not prove the
    sentence's interpretation is correct.
    """
    claims: list[ClaimCheck] = []
    for sentence in _iter_sentences(report):
        clean = sentence.strip()
        if len(clean) < 20 or not CLAIM_SIGNAL_RE.search(clean):
            continue
        local = list(LOCAL_RE.finditer(clean))
        if local:
            candidates = [_claim_from_local(clean, match, resolver) for match in local]
            rank = {
                "supported_quote": 4,
                "page_only": 3,
                "citation_failed": 2,
                "external_unchecked": 1,
                "no_citation": 0,
            }
            claim = max(candidates, key=lambda item: rank[item.status])
        else:
            external = EXTERNAL_LINK_RE.search(clean)
            if external:
                claim = ClaimCheck(
                    sentence=clean[:500],
                    citation=external.group(0),
                    kind="external_url",
                    status="external_unchecked",
                    reason="外部链接未联网核验；不能证明句子被来源支持",
                )
            else:
                claim = ClaimCheck(
                    sentence=clean[:500],
                    kind="none",
                    status="no_citation",
                    reason="包含事实/数值/比较信号，但同一句没有本地引用或外部链接",
                )
        claims.append(claim)
        if len(claims) >= limit:
            break
    return claims


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
        for part in (part.strip() for part in parts if part.strip()):
            # A citation often follows the sentence punctuation:
            #   "OA is 98.4%。[[doc:d1 p.1]]"
            # Attach marker-only fragments to the previous sentence so the
            # numeric claim is not falsely reported as uncited.
            if LOCAL_RE.fullmatch(part) and sentences:
                sentences[-1] = f"{sentences[-1]} {part}"
            else:
                sentences.append(part)
    return sentences


def find_unsupported_claims(report: str, *, limit: int = 50) -> list[UnsupportedClaim]:
    claims: list[UnsupportedClaim] = []
    seen: set[str] = set()
    for sentence in _iter_sentences(report):
        if not METRIC_CLAIM_RE.search(sentence) or not NUMBER_RE.search(sentence):
            continue
        if (
            LOCAL_RE.search(sentence)
            or EXTERNAL_LINK_RE.search(sentence)
            or LOCAL_FILE_LINK_RE.search(sentence)
        ):
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

    for match in LOCAL_FILE_LINK_RE.finditer(report):
        checks.append(
            CitationCheck(
                raw=match.group(0),
                kind="local_file",
                filename=match.group(2),
                status="local_file_unverified",
                message="相对 PDF 文件链接；缺少页码与文档 ID，无法做页级/原文核验",
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
    local_file_unverified = sum(1 for check in checks if check.kind == "local_file")
    failed = sum(
        1
        for check in checks
        if check.kind == "local_pdf" and check.status not in {"verified_quote", "verified_page_only"}
    )
    unsupported = [] if skip_claims else find_unsupported_claims(report)
    claims = [] if skip_claims else audit_claims(report, resolver)

    return CitationAudit(
        total=len(checks),
        verified_local=verified_local,
        page_only_local=page_only,
        failed_local=failed,
        external_unchecked=external,
        local_file_unverified=local_file_unverified,
        unsupported_claims=unsupported,
        claims=claims,
        claims_supported=sum(1 for claim in claims if claim.status == "supported_quote"),
        claims_page_only=sum(1 for claim in claims if claim.status == "page_only"),
        claims_external_unchecked=sum(
            1 for claim in claims if claim.status == "external_unchecked"
        ),
        claims_no_citation=sum(1 for claim in claims if claim.status == "no_citation"),
        claims_failed=sum(1 for claim in claims if claim.status == "citation_failed"),
        checks=checks,
        checked_at=datetime.now(UTC).isoformat(timespec="seconds"),
        scope_note=(
            "本报告只核验引文是否存在于指定 PDF 页码，并做 claim-to-citation 映射；"
            "不验证事实语义、论文质量或实验可比性。外部 URL 未联网核验；"
            "相对 PDF 文件名链接缺少页码/文档 ID，只能标记为未做页级核验。"
        ),
    )


def render_audit_markdown(audit: CitationAudit) -> str:
    lines = [
        "## 引用核验报告",
        "",
        f"- 本地 PDF 引用：{audit.total - audit.external_unchecked} 条；"
        f"原文片段核验通过 {audit.verified_local} 条；仅页码核验 {audit.page_only_local} 条；"
        f"失败 {audit.failed_local} 条。",
        f"- 外部链接：{audit.external_unchecked} 条（未联网核验）。",
        f"- 本地 PDF 文件链接：{audit.local_file_unverified} 条（无页码/文档 ID，未做页级核验）。",
        f"- 缺少引用的数值性结论：{len(audit.unsupported_claims)} 条。",
        f"- Claim-level：逐字支持 {audit.claims_supported} 条；仅页码 {audit.claims_page_only} 条；"
        f"外部未核验 {audit.claims_external_unchecked} 条；无引用 {audit.claims_no_citation} 条；"
        f"引用失败 {audit.claims_failed} 条。",
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
    if audit.claims:
        weak = [claim for claim in audit.claims if claim.status != "supported_quote"]
        if weak:
            lines += ["### Claim-level 未逐字支持的句子（最多 10 条）", ""]
            for claim in weak[:10]:
                lines.append(f"- `{claim.status}` {claim.sentence}")
            lines.append("")
    lines += [
        "> 核验边界：原文出现 ≠ 事实正确 ≠ 实验可比。页码与片段匹配只证明引用可追溯，"
        "不代表语义验证；外部链接未联网核验。",
        "",
    ]
    return "\n".join(lines)


def append_audit_section(report: str, audit: CitationAudit) -> str:
    if "## 引用核验报告" in report:
        return report
    return report.rstrip() + "\n\n" + render_audit_markdown(audit)
