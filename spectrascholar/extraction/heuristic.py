"""Deterministic, offline paper extraction.

The heuristic extractor never invents a value.  It only reports:

* strings that literally occur in the PDF text;
* a page number and a contiguous quote;
* a confidence label explaining how the value was located.

Metrics found in prose are explicitly marked as "association inferred from a
text window" because this version does not parse table structure.
"""
from __future__ import annotations

import re
import time

from ..evidence import make_evidence_ref, snippet_around, title_hint
from ..schemas import (
    DatasetRecord,
    EvidenceRef,
    ExperimentCondition,
    ExtractedField,
    ExtractionStats,
    GraphConstructionRecord,
    MethodRecord,
    MetricRecord,
    PaperExtraction,
    PaperMetadata,
)

DATASET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Indian Pines", re.compile(r"Indian\s+Pines", re.IGNORECASE)),
    ("Pavia University", re.compile(r"(?:Pavia\s+University|University\s+of\s+Pavia)", re.IGNORECASE)),
    ("Pavia Centre", re.compile(r"Pavia\s+Cent(?:re|er)", re.IGNORECASE)),
    ("Salinas", re.compile(r"\bSalinas\b", re.IGNORECASE)),
    ("Houston 2013", re.compile(r"Houston\s+2013", re.IGNORECASE)),
    ("Houston", re.compile(r"\bHouston\b", re.IGNORECASE)),
    ("Berlin", re.compile(r"\bBerlin\b", re.IGNORECASE)),
    ("Augsburg", re.compile(r"\bAugsburg\b", re.IGNORECASE)),
    ("Botswana", re.compile(r"\bBotswana\b", re.IGNORECASE)),
    ("Trento", re.compile(r"\bTrento\b", re.IGNORECASE)),
    ("MUUFL", re.compile(r"\bMUUFL\b", re.IGNORECASE)),
    ("Long Island", re.compile(r"Long\s+Island", re.IGNORECASE)),
    ("WHU-Hi", re.compile(r"WHU[-\s]?Hi", re.IGNORECASE)),
    ("Kennedy Space Center", re.compile(r"Kennedy\s+Space\s+Center", re.IGNORECASE)),
    ("Mantua", re.compile(r"\bMantua\b", re.IGNORECASE)),
]

# Canonical name, regex, family.  Specific architectures come first so that a
# generic "CNN" mention does not create a duplicate method.
MODEL_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("HybridSN", re.compile(r"\bHybridSN\b", re.IGNORECASE), "CNN"),
    ("SSRN", re.compile(r"\bSSRN\b", re.IGNORECASE), "CNN"),
    ("SpectralFormer", re.compile(r"\bSpectralFormer\b", re.IGNORECASE), "Transformer"),
    ("SSTN", re.compile(r"\bSSTN\b"), "Transformer"),
    ("GraphSAGE", re.compile(r"\bGraphSAGE\b", re.IGNORECASE), "GNN"),
    ("GAT", re.compile(r"\bGAT\b"), "GNN"),
    ("GCN", re.compile(r"\bGCN\b"), "GNN"),
    ("GIN", re.compile(r"\bGIN\b"), "GNN"),
    ("ResNet", re.compile(r"\bResNet(?:-\d+)?\b", re.IGNORECASE), "CNN"),
    ("ViT", re.compile(r"\bViT\b"), "Transformer"),
    ("3D-CNN", re.compile(r"\b3D[-\s]?CNN\b", re.IGNORECASE), "CNN"),
    ("2D-CNN", re.compile(r"\b2D[-\s]?CNN\b", re.IGNORECASE), "CNN"),
    ("Transformer", re.compile(r"\bTransformer(?:s)?\b", re.IGNORECASE), "Transformer"),
    ("Graph Neural Network", re.compile(r"\bgraph\s+neural\s+network(?:s)?\b", re.IGNORECASE), "GNN"),
    ("Convolutional Neural Network", re.compile(r"\bconvolutional\s+neural\s+network(?:s)?\b", re.IGNORECASE), "CNN"),
    ("CNN", re.compile(r"\bCNN(?:s)?\b"), "CNN"),
    ("GNN", re.compile(r"\bGNN(?:s)?\b"), "GNN"),
]

GRAPH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("KNN", re.compile(r"\bKNN\b|k[-\s]?nearest\s+neighbou?rs?", re.IGNORECASE)),
    ("RBF", re.compile(r"\bRBF\b|radial\s+basis\s+function|Gaussian\s+kernel", re.IGNORECASE)),
    ("dynamic", re.compile(r"\bdynamic\s+graph(?:s)?\b|动态图|自适应图|adaptive\s+graph", re.IGNORECASE)),
    ("static", re.compile(r"\bstatic\s+graph(?:s)?\b|静态图|fixed\s+graph", re.IGNORECASE)),
    ("superpixel", re.compile(r"\bsuperpixel(?:s)?\b", re.IGNORECASE)),
    ("spectral", re.compile(r"spectral[-\s]?similarity\s+graph|spectral\s+graph", re.IGNORECASE)),
]

METRIC_RE = re.compile(
    r"(?P<label>\bOA\b|\bAA\b|overall\s+accuracy|average\s+accuracy|\bKappa\b|κ)"
    r"(?:\s*\([^)]{0,24}\))?"
    r"\s*(?:of|is|was|reaches|achieves|=|:|为|达到)?\s*"
    r"(?P<num>\d{1,3}(?:\.\d+)?)\s*(?P<pct>%?)",
    re.IGNORECASE,
)
TRAIN_RATIO_RE = re.compile(
    r"(?P<num>\d{1,2}(?:\.\d+)?)\s*%\s*(?:of\s+)?"
    r"(?:the\s+)?(?:training|labeled|labelled|training\s+samples?|samples?)",
    re.IGNORECASE,
)
TRAIN_RATIO_RE_ALT = re.compile(
    r"(?:training|labeled|labelled)[^.\n]{0,30}?(?P<num>\d{1,2}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
PATCH_SIZE_RE = re.compile(
    r"(?:patch(?:es)?\s*(?:size)?\s*(?:of|is|was|=|:)?\s*)"
    r"(?P<w>\d{1,3})\s*(?:×|x|\*)\s*(?P<h>\d{1,3})",
    re.IGNORECASE,
)
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
VENUE_RE = re.compile(
    r"(IEEE\s+Transactions\s+on\s+[A-Z][A-Za-z\s&]{2,50}|"
    r"Proceedings\s+of\s+[A-Z][A-Za-z\s&]{2,60}|"
    r"IGARSS\s+\d{4}|CVPR\s*\d{0,4}|ICCV\s*\d{0,4}|ECCV\s*\d{0,4}|"
    r"NeurIPS\s*\d{0,4}|AAAI\s*\d{0,4}|IJCAI\s*\d{0,4}|"
    r"arXiv\s+preprint)",
    re.IGNORECASE,
)


def infer_family(text: str) -> str | None:
    """Map a method name/quote to a coarse model family.

    This is a deterministic label, not an LLM judgement.  It uses the same
    vocabulary as :data:`MODEL_PATTERNS`; ``None`` means "not enough evidence".
    """
    lowered = text.casefold()
    if re.search(r"\b(hybridsn|ssrn|resnet|cnn|convolutional)\b", lowered):
        return "CNN"
    if re.search(r"\b(gcn|gat|gin|graphsage|gnn|graph\s+neural\s+network)\b", lowered):
        return "GNN"
    if re.search(r"\b(transformer|vit|spectralformer|sstn)\b", lowered):
        return "Transformer"
    return None


def _find_pattern_evidence(
    document_id: str,
    pages: list[str],
    pattern: re.Pattern[str],
    *,
    value_group: int | str | None = None,
) -> EvidenceRef | None:
    for page_no, text in enumerate(pages, 1):
        match = pattern.search(text)
        if not match:
            continue
        value = match.group(0)
        if value_group is not None:
            value = match.group(value_group)
        quote = snippet_around(text, match.start(), match.end())
        return make_evidence_ref(document_id, pages, page_no, quote, value=value)
    return None


def _first_page_match(pages: list[str], pattern: re.Pattern[str]) -> tuple[int, re.Match[str]] | None:
    for page_no, text in enumerate(pages, 1):
        match = pattern.search(text)
        if match:
            return page_no, match
    return None


def _extract_title(document_id: str, pages: list[str]) -> ExtractedField:
    hint = title_hint(pages)
    if not hint:
        return ExtractedField(value=None, method="heuristic", confidence="low", note="未能从首页版面推断标题")
    evidence = make_evidence_ref(
        document_id,
        pages,
        1,
        hint,
        value=hint,
        note="版面推断：首页首个长文本行，可能是标题；请人工确认",
    )
    return ExtractedField(value=hint, evidence=[evidence], method="heuristic", confidence="low")


def _extract_authors(document_id: str, pages: list[str], title: str | None) -> ExtractedField:
    if not pages or not title:
        return ExtractedField(value=None, note="缺少标题，未尝试推断作者")
    lines = [line.strip() for line in pages[0].splitlines() if line.strip()]
    try:
        index = lines.index(title)
    except ValueError:
        index = 0
    for candidate in lines[index + 1 : index + 4]:
        if not 5 <= len(candidate) <= 300:
            continue
        lowered = candidate.lower()
        if any(word in lowered for word in ("abstract", "keywords", "university", "institute", "email", "@")):
            continue
        words = candidate.split()
        capitalized = [word for word in words if word[:1].isupper()]
        if len(capitalized) >= 2 and sum(char.isalpha() for char in candidate) >= 6:
            evidence = make_evidence_ref(
                document_id,
                pages,
                1,
                candidate,
                value=candidate,
                note="版面推断：标题后作者行；上标和机构需人工剥离",
            )
            return ExtractedField(
                value=" ".join(candidate.split()),
                evidence=[evidence],
                method="heuristic",
                confidence="low",
                note="作者行来自版面推断，未做姓名消歧",
            )
    return ExtractedField(value=None, note="未能可靠定位作者行")


def _extract_year(document_id: str, pages: list[str]) -> ExtractedField:
    context_re = re.compile(
        r"(IEEE|CVPR|ICCV|ECCV|IGARSS|NeurIPS|AAAI|IJCAI|ACM|arXiv|published|copyright|©)",
        re.IGNORECASE,
    )
    fallback: tuple[int, re.Match[str]] | None = None
    for page_no, text in enumerate(pages[:2], 1):
        for match in YEAR_RE.finditer(text):
            year = int(match.group(0))
            if not 1980 <= year <= 2100:
                continue
            start = max(0, match.start() - 90)
            end = min(len(text), match.end() + 90)
            if context_re.search(text[start:end]):
                quote = snippet_around(text, match.start(), match.end())
                evidence = make_evidence_ref(document_id, pages, page_no, quote, value=match.group(0))
                return ExtractedField(
                    value=match.group(0),
                    evidence=[evidence],
                    method="heuristic",
                    confidence="medium",
                    note="从出版/会议上下文推断；不是文献库元数据",
                )
            if fallback is None:
                fallback = (page_no, match)
    if fallback:
        page_no, match = fallback
        quote = snippet_around(text=pages[page_no - 1], start=match.start(), end=match.end())
        evidence = make_evidence_ref(document_id, pages, page_no, quote, value=match.group(0))
        return ExtractedField(
            value=match.group(0),
            evidence=[evidence],
            method="heuristic",
            confidence="low",
            note="首页出现的年份，可能与出版年无关",
        )
    return ExtractedField(value=None, note="未找到可靠年份")


def _extract_venue(document_id: str, pages: list[str]) -> ExtractedField:
    found = _first_page_match(pages[:2], VENUE_RE)
    if not found:
        return ExtractedField(value=None, note="未识别到期刊/会议名称")
    page_no, match = found
    quote = snippet_around(pages[page_no - 1], match.start(), match.end())
    evidence = make_evidence_ref(document_id, pages, page_no, quote, value=match.group(0))
    return ExtractedField(
        value=" ".join(match.group(0).split()),
        evidence=[evidence],
        method="heuristic",
        confidence="low",
        note="正则识别的出版载体，可能是页眉或参考文献",
    )


def _extract_methods(document_id: str, pages: list[str]) -> list[MethodRecord]:
    methods: list[MethodRecord] = []
    specific_families: set[str] = set()
    for canonical, pattern, family in MODEL_PATTERNS:
        if (
            canonical
            in {"CNN", "GNN", "Transformer", "Graph Neural Network", "Convolutional Neural Network"}
            and family in specific_families
        ):
            continue
        evidence = _find_pattern_evidence(document_id, pages, pattern)
        if evidence is None:
            continue
        methods.append(
            MethodRecord(
                name=canonical,
                family=family,
                evidence=[evidence],
                note="模型名称按关键词字面匹配，不等同于论文提出的方法",
            )
        )
        if canonical not in {"CNN", "GNN", "Transformer", "Graph Neural Network", "Convolutional Neural Network"}:
            specific_families.add(family)
    return methods


def _extract_graph_constructions(document_id: str, pages: list[str]) -> list[GraphConstructionRecord]:
    records: list[GraphConstructionRecord] = []
    for kind, pattern in GRAPH_PATTERNS:
        evidence = _find_pattern_evidence(document_id, pages, pattern)
        if evidence:
            records.append(GraphConstructionRecord(kind=kind, evidence=[evidence]))
    return records


def _extract_datasets(document_id: str, pages: list[str]) -> list[DatasetRecord]:
    records: list[DatasetRecord] = []
    seen: set[str] = set()
    for name, pattern in DATASET_PATTERNS:
        if name == "Houston" and "Houston 2013" in seen:
            continue
        evidence = _find_pattern_evidence(document_id, pages, pattern)
        if evidence:
            records.append(DatasetRecord(name=name, evidence=[evidence]))
            seen.add(name)
    return records


def _sentence_window(text: str, start: int, end: int) -> str:
    """Return a contiguous context window around a match.

    A pure newline/sentence boundary is too narrow for PDFs, where the dataset
    and training ratio often sit on the preceding line.  The window is still a
    contiguous original substring, so the quote verifier can prove it exists.
    """
    return snippet_around(text, start, end, window=260)


def _metric_name(label: str) -> str:
    lowered = label.lower().strip()
    if lowered == "oa" or "overall" in lowered:
        return "OA"
    if lowered == "aa" or "average" in lowered:
        return "AA"
    if "kappa" in lowered or label == "κ":
        return "Kappa"
    return label.strip()


def _train_ratio_in(text: str) -> str | None:
    match = TRAIN_RATIO_RE.search(text) or TRAIN_RATIO_RE_ALT.search(text)
    if not match:
        return None
    return f"{match.group('num')}%"


def _patch_size_in(text: str) -> str | None:
    match = PATCH_SIZE_RE.search(text)
    if not match:
        return None
    return f"{match.group('w')}x{match.group('h')}"


def _protocol_in(text: str) -> str | None:
    lowered = text.casefold()
    if re.search(r"random(?:ly)?\s+(?:split|sampl|select)|随机(?:划分|采样|选取)", lowered):
        return "随机划分/采样"
    if re.search(r"fixed\s+(?:split|training)|固定(?:划分|训练集)|geographical\s+split", lowered):
        return "固定/地理划分"
    if re.search(r"cross[-\s]?validation|交叉验证", lowered):
        return "交叉验证"
    return None


def _dataset_in(text: str) -> str | None:
    matches = [name for name, pattern in DATASET_PATTERNS if pattern.search(text)]
    matches = [name for name in matches if not (name == "Houston" and "Houston 2013" in matches)]
    return matches[0] if len(matches) == 1 else None


def _extract_metrics(document_id: str, pages: list[str]) -> list[MetricRecord]:
    records: list[MetricRecord] = []
    seen: set[tuple[str | None, str, str, int]] = set()
    for page_no, text in enumerate(pages, 1):
        for match in METRIC_RE.finditer(text):
            raw_number = match.group("num")
            try:
                numeric = float(raw_number)
            except ValueError:
                continue
            if numeric > 100:
                continue
            metric = _metric_name(match.group("label"))
            if metric not in {"OA", "AA", "Kappa"}:
                continue
            value = f"{raw_number}%" if match.group("pct") else raw_number
            quote = _sentence_window(text, match.start(), match.end())
            dataset = _dataset_in(quote)
            train_ratio = _train_ratio_in(quote)
            patch_size = _patch_size_in(quote)
            protocol = _protocol_in(quote)
            key = (dataset, metric, value, page_no)
            if key in seen:
                continue
            seen.add(key)
            evidence = make_evidence_ref(
                document_id,
                pages,
                page_no,
                quote,
                value=raw_number,
                note=(
                    "指标数值与数据集/训练比例的关联来自同一文本窗口；"
                    "本版本不解析表格结构，需人工核对行列对应关系"
                ),
            )
            records.append(
                MetricRecord(
                    dataset=dataset,
                    metric=metric,
                    value=value,
                    train_ratio=train_ratio,
                    patch_size=patch_size,
                    protocol=protocol,
                    evidence=[evidence],
                    note="从正文文本窗口抽取，不等同于表格解析",
                )
            )
    return records


def _extract_conditions(document_id: str, pages: list[str]) -> list[ExperimentCondition]:
    conditions: list[ExperimentCondition] = []
    seen: set[tuple[str | None, str | None, int]] = set()
    for page_no, text in enumerate(pages, 1):
        for regex in (TRAIN_RATIO_RE, TRAIN_RATIO_RE_ALT):
            for match in regex.finditer(text):
                quote = _sentence_window(text, match.start(), match.end())
                dataset = _dataset_in(quote)
                ratio = f"{match.group('num')}%"
                key = (dataset, ratio, page_no)
                if key in seen:
                    continue
                seen.add(key)
                evidence = make_evidence_ref(document_id, pages, page_no, quote, value=ratio)
                conditions.append(
                    ExperimentCondition(
                        dataset=dataset,
                        train_ratio=ratio,
                        patch_size=_patch_size_in(quote),
                        protocol=_protocol_in(quote),
                        evidence=[evidence],
                        note="训练比例来自文本窗口，需核对是否对应同一数据集与划分",
                    )
                )
        for match in PATCH_SIZE_RE.finditer(text):
            quote = _sentence_window(text, match.start(), match.end())
            dataset = _dataset_in(quote)
            size = f"{match.group('w')}x{match.group('h')}"
            key = (dataset, size, page_no)
            if key in seen:
                continue
            seen.add(key)
            evidence = make_evidence_ref(document_id, pages, page_no, quote, value=size)
            conditions.append(
                ExperimentCondition(
                    dataset=dataset,
                    patch_size=size,
                    evidence=[evidence],
                    note="输入补丁尺寸来自文本窗口",
                )
            )
    return conditions


def _missing_fields(
    metadata: PaperMetadata,
    methods: list[MethodRecord],
    datasets: list[DatasetRecord],
    graphs: list[GraphConstructionRecord],
    conditions: list[ExperimentCondition],
    metrics: list[MetricRecord],
) -> list[str]:
    missing: list[str] = []
    for name in ("title", "authors", "year", "venue"):
        if getattr(metadata, name).missing:
            missing.append(f"metadata.{name}")
    if not methods:
        missing.append("methods")
    if not datasets:
        missing.append("datasets")
    if not graphs:
        missing.append("graph_constructions")
    if not conditions:
        missing.append("experiment_conditions")
    if not metrics:
        missing.append("metrics")
    return missing


def extract_heuristic(document_id: str, filename: str, pages: list[str]) -> PaperExtraction:
    """Extract literal candidates and attach page-level evidence."""
    started = time.perf_counter()
    metadata = PaperMetadata(
        title=_extract_title(document_id, pages),
        authors=_extract_authors(document_id, pages, title_hint(pages)),
        year=_extract_year(document_id, pages),
        venue=_extract_venue(document_id, pages),
    )
    methods = _extract_methods(document_id, pages)
    datasets = _extract_datasets(document_id, pages)
    graphs = _extract_graph_constructions(document_id, pages)
    conditions = _extract_conditions(document_id, pages)
    metrics = _extract_metrics(document_id, pages)
    missing = _missing_fields(metadata, methods, datasets, graphs, conditions, metrics)

    notes = [
        "离线规则模式：只保留能在 PDF 文本中逐字定位的候选值，不补全缺失字段。",
        "指标来自正文文本窗口而非表格结构解析；同一数据集、不同训练比例/划分的数值不可直接排名。",
    ]
    if not any(text.strip() for text in pages):
        notes.append("PDF 未提取到有效文本，可能需要 OCR；本版本不提供 OCR。")
    if any(not text.strip() for text in pages):
        notes.append("部分页面没有可提取文本（可能是扫描页或纯图片表格）。")

    evidence_items = [
        evidence
        for field in (metadata.title, metadata.authors, metadata.year, metadata.venue)
        for evidence in field.evidence
    ]
    evidence_items += [item for method in methods for item in method.evidence]
    evidence_items += [item for dataset in datasets for item in dataset.evidence]
    evidence_items += [item for graph in graphs for item in graph.evidence]
    evidence_items += [item for condition in conditions for item in condition.evidence]
    evidence_items += [item for metric in metrics for item in metric.evidence]
    accepted = sum(1 for item in evidence_items if item.accepted)

    return PaperExtraction(
        document_id=document_id,
        filename=filename,
        extraction_mode="heuristic",
        metadata=metadata,
        methods=methods,
        datasets=datasets,
        graph_constructions=graphs,
        experiment_conditions=conditions,
        metrics=metrics,
        missing_fields=missing,
        notes=notes,
        stats=ExtractionStats(
            pages_scanned=len(pages),
            characters_scanned=sum(len(text) for text in pages),
            candidates=len(evidence_items),
            accepted=accepted,
            rejected=len(evidence_items) - accepted,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        ),
    )
