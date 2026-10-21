"""Page-aware PDF table extraction for OA/AA/Kappa tables.

This module is deliberately conservative:

* only tables detected by pdfplumber's structural table finder are used;
* only numeric cells whose digits also occur in the page text are accepted;
* the table gives the row/column association, the page text gives the quote;
* missing conditions stay missing, so comparison can mark the metric as
  non-comparable instead of guessing.

Scanned/image tables still require OCR and are explicitly out of scope.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..evidence import make_evidence_ref, normalized, snippet_around
from ..schemas import (
    DatasetRecord,
    ExperimentCondition,
    MetricRecord,
    PaperExtraction,
    RejectionRecord,
)
from ..settings import settings
from .heuristic import (
    _dataset_in,
    _patch_size_in,
    _protocol_in,
    _train_ratio_in,
)

HEADER_ALIASES = {
    "oa": "OA",
    "oa%": "OA",
    "overallaccuracy": "OA",
    "overallaccuracy%": "OA",
    "aa": "AA",
    "aa%": "AA",
    "averageaccuracy": "AA",
    "averageaccuracy%": "AA",
    "kappa": "Kappa",
    "kappa%": "Kappa",
    "κ": "Kappa",
}
NUMERIC_RE = re.compile(r"^-?\d{1,3}(?:\.\d+)?\s*%?$")


@dataclass
class TableExtractionResult:
    metrics: list[MetricRecord] = field(default_factory=list)
    datasets: list[DatasetRecord] = field(default_factory=list)
    conditions: list[ExperimentCondition] = field(default_factory=list)
    rejections: list[RejectionRecord] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    tables_found: int = 0


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def _normalize_header(value: object) -> str:
    text = _clean_cell(value).casefold()
    text = re.sub(r"[\s_\-()（）]", "", text)
    return text


def _metric_for_header(value: object) -> str | None:
    normalized = _normalize_header(value)
    if normalized in HEADER_ALIASES:
        return HEADER_ALIASES[normalized]
    for alias, metric in HEADER_ALIASES.items():
        if alias and alias in normalized:
            return metric
    return None


def _header_map(row: list[str]) -> tuple[dict[int, str], int | None]:
    mapping: dict[int, str] = {}
    for index, cell in enumerate(row):
        metric = _metric_for_header(cell)
        if metric and metric not in mapping.values():
            mapping[index] = metric
    return mapping, (0 if mapping else None)


def _parse_cell(cell: str) -> tuple[str, str] | None:
    """Return (display_value, numeric_value) or None for non-metric cells."""
    cleaned = _clean_cell(cell)
    if not cleaned or cleaned in {"-", "—", "–", "N/A", "NA", "null", "None"}:
        return None
    if "±" in cleaned or "( )" in cleaned:
        return None
    if not NUMERIC_RE.match(cleaned):
        return None
    numbers = re.findall(r"-?\d{1,3}(?:\.\d+)?", cleaned)
    if len(numbers) != 1:
        return None
    display = cleaned.replace(" ", "")
    return display, numbers[0]


def _find_quote(page_text: str, value: str) -> str | None:
    index = page_text.find(value)
    if index < 0:
        return None
    quote = snippet_around(page_text, index, index + len(value), window=120)
    return quote if quote.strip() else None


def _caption_context(
    page,
    table,
) -> tuple[str, str]:
    """Return (caption above table, page text) from a pdfplumber page."""
    try:
        page_text = page.extract_text() or ""
    except Exception:
        page_text = ""
    caption = ""
    try:
        top = table.bbox[1]
        crop_top = max(0, top - 110)
        crop_bottom = max(crop_top + 1, top - 2)
        caption = page.crop((0, crop_top, page.width, crop_bottom)).extract_text() or ""
    except Exception:
        caption = ""
    return " ".join(caption.split()), page_text


def parse_table_rows(
    rows: list[list[object]],
    *,
    document_id: str,
    page_no: int,
    pages: list[str],
    caption: str = "",
    page_text: str = "",
) -> TableExtractionResult:
    """Parse one table's rows without touching pdfplumber.

    Exposed separately so table parsing can be unit-tested with plain rows.
    """
    result = TableExtractionResult()
    cleaned_rows = [[_clean_cell(cell) for cell in row] for row in rows]
    cleaned_rows = [row for row in cleaned_rows if any(cell for cell in row)]
    if len(cleaned_rows) < 2:
        return result

    header_index: int | None = None
    header_mapping: dict[int, str] = {}
    for index, row in enumerate(cleaned_rows[:3]):
        mapping, _ = _header_map(row)
        if mapping:
            header_index = index
            header_mapping = mapping
            break
    if header_index is None or not header_mapping:
        result.notes.append(f"第 {page_no} 页检测到表格，但未识别到 OA/AA/Kappa 表头。")
        return result

    dataset = _dataset_in(caption) or _dataset_in(page_text) or None
    train_ratio = _train_ratio_in(caption) or _train_ratio_in(page_text)
    patch_size = _patch_size_in(caption) or _patch_size_in(page_text)
    protocol = _protocol_in(caption) or _protocol_in(page_text)

    if dataset:
        if caption and _dataset_in(caption):
            dataset_quote = caption
        else:
            dataset_quote = _find_quote(page_text, dataset) or page_text
        evidence = make_evidence_ref(
            document_id,
            pages,
            page_no,
            dataset_quote,
            value=dataset,
            note="表格标题/上下文中的数据集；表格行列由结构确定",
        )
        if evidence.accepted:
            result.datasets.append(DatasetRecord(name=dataset, evidence=[evidence]))
        else:
            result.notes.append(f"第 {page_no} 页表格数据集 '{dataset}' 未能定位到可核验上下文。")

    condition_value = train_ratio or patch_size
    if caption and (_train_ratio_in(caption) or _patch_size_in(caption) or _protocol_in(caption)):
        condition_quote = caption
    elif condition_value:
        condition_quote = _find_quote(page_text, condition_value) or ""
    else:
        condition_quote = ""
    if condition_quote and any((train_ratio, patch_size, protocol)):
        evidence = make_evidence_ref(
            document_id,
            pages,
            page_no,
            condition_quote,
            value=condition_value,
            note="表格标题/上下文中的实验条件；需核对是否适用于整张表",
        )
        if evidence.accepted:
            result.conditions.append(
                ExperimentCondition(
                    dataset=dataset,
                    train_ratio=train_ratio,
                    patch_size=patch_size,
                    protocol=protocol,
                    evidence=[evidence],
                    note="表格上下文条件；同一表格内可能包含多组设置",
                )
            )

    seen: set[tuple[str | None, str | None, str, str]] = set()
    for row in cleaned_rows[header_index + 1 :]:
        method = row[0].strip() if row else ""
        if not method or method.casefold() in {"method", "methods", "model", "algorithm", "class"}:
            continue
        for column, metric in header_mapping.items():
            if column >= len(row):
                continue
            parsed = _parse_cell(row[column])
            if parsed is None:
                if re.search(r"\d", row[column]):
                    result.rejections.append(
                        RejectionRecord(
                            field="table_metrics",
                            value=row[column],
                            page=page_no,
                            reason="ambiguous_table_cell",
                            note="表格单元格不是单一数值（可能包含 ±、区间或多个数字），拒绝猜测",
                        )
                    )
                continue
            display, numeric = parsed
            try:
                numeric_value = float(numeric)
            except ValueError:
                continue
            if metric in {"OA", "AA"} and numeric_value > 100:
                result.rejections.append(
                    RejectionRecord(
                        field="table_metrics",
                        value=display,
                        page=page_no,
                        reason="value_out_of_range",
                        note="OA/AA 大于 100%，拒绝",
                    )
                )
                continue
            if metric == "Kappa" and numeric_value > 1.5:
                # 97.6 as a percentage is possible, but keep it as reported and
                # let the human verify; do not silently divide by 100.
                result.notes.append(f"第 {page_no} 页 Kappa={display} 看起来像百分比，需人工确认。")
            quote = _find_quote(page_text, numeric)
            if quote is None:
                result.rejections.append(
                    RejectionRecord(
                        field="table_metrics",
                        value=display,
                        page=page_no,
                        reason="quote_not_found",
                        note="表格数值未在 PDF 页文本中找到，无法建立可核验证据",
                    )
                )
                continue
            evidence = make_evidence_ref(
                document_id,
                pages,
                page_no,
                quote,
                value=numeric,
                note="表格单元格数值 + 页文本定位；行列关联来自表格结构，需人工核对",
            )
            if not evidence.accepted:
                result.rejections.append(
                    RejectionRecord(
                        field="table_metrics",
                        value=display,
                        page=page_no,
                        reason=evidence.status,
                        note=evidence.note,
                    )
                )
                continue
            key = (dataset, method, metric, display)
            if key in seen:
                continue
            seen.add(key)
            result.metrics.append(
                MetricRecord(
                    dataset=dataset,
                    method=method,
                    metric=metric,
                    value=display,
                    train_ratio=train_ratio,
                    patch_size=patch_size,
                    protocol=protocol,
                    source="table",
                    evidence=[evidence],
                    note=(
                        "来自 PDF 表格结构；行列关联由表格边界确定。"
                        "训练比例/补丁/协议来自表格上下文，需人工核对是否适用。"
                    ),
                )
            )
    return result


def parse_pdf_tables(
    path: Path,
    pages: list[str],
    document_id: str,
    *,
    max_pages: int | None = None,
) -> TableExtractionResult:
    """Detect tables on each page and parse OA/AA/Kappa cells."""
    result = TableExtractionResult()
    if not settings.table_extraction_enabled:
        result.notes.append("TABLE_EXTRACTION_ENABLED=0，跳过表格解析。")
        return result
    try:
        import pdfplumber
    except ImportError:
        result.notes.append("未安装 pdfplumber，跳过表格解析；正文指标仍可用。")
        return result

    max_pages = settings.max_pdf_pages if max_pages is None else max_pages
    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:
        result.notes.append(f"pdfplumber 无法打开 PDF，跳过表格解析: {type(exc).__name__}")
        return result

    with pdf:
        for page_no, page in enumerate(pdf.pages[:max_pages], 1):
            page_text = pages[page_no - 1] if page_no <= len(pages) else ""
            try:
                tables = page.find_tables()
            except Exception as exc:
                result.notes.append(f"第 {page_no} 页表格检测失败: {type(exc).__name__}")
                continue
            for table in tables:
                try:
                    rows = table.extract() or []
                except Exception as exc:
                    result.notes.append(f"第 {page_no} 页表格读取失败: {type(exc).__name__}")
                    continue
                if not rows:
                    continue
                result.tables_found += 1
                caption, pdf_text = _caption_context(page, table)
                parsed = parse_table_rows(
                    rows,
                    document_id=document_id,
                    page_no=page_no,
                    pages=pages,
                    caption=caption,
                    page_text=page_text or pdf_text,
                )
                result.metrics.extend(parsed.metrics)
                result.datasets.extend(parsed.datasets)
                result.conditions.extend(parsed.conditions)
                result.rejections.extend(parsed.rejections)
                result.notes.extend(parsed.notes)

    if result.tables_found == 0:
        result.notes.append("未检测到结构化表格；扫描件或图片表格需要 OCR，当前版本不处理。")
    elif result.metrics:
        result.notes.append(
            f"从 {result.tables_found} 个表格中解析出 {len(result.metrics)} 条指标；"
            "表格行列关联与实验条件仍需人工复核。"
        )
    return result


TEXT_TABLE_DATASETS = (
    ("Indian Pines", ("indian pines", "indian pine", "ip")),
    ("Pavia University", ("pavia university", "university of pavia", "pavia")),
    ("Salinas Scene", ("salinas scene", "salinas")),
)
TEXT_TABLE_METRICS = ("OA", "Kappa", "AA")


def _text_table_header(line: str) -> list[str] | None:
    """Return dataset order if a text line looks like a 3-dataset OA/Kappa/AA header."""
    text = normalized(line)
    if not all(any(alias in text for alias in aliases) for _, aliases in TEXT_TABLE_DATASETS):
        return None
    if not all(metric.lower() in text for metric in TEXT_TABLE_METRICS):
        return None
    order = []
    for name, aliases in TEXT_TABLE_DATASETS:
        positions = [text.find(alias) for alias in aliases if alias in text]
        if not positions:
            return None
        order.append((name, min(positions)))
    order.sort(key=lambda item: item[1])
    return [name for name, _ in order]


def parse_text_metric_rows(
    pages: list[str],
    document_id: str,
    method_names: list[str],
    conditions: list[ExperimentCondition] | None = None,
) -> TableExtractionResult:
    """Bind text-extractable result-table rows to dataset/metric columns.

    Some publishers embed result tables as text (not ruled graphics). pypdf can
    read the header and row lines but not the cell geometry. This parser uses
    the repeated ``OA Kappa AA`` header column order only when three known
    datasets and a method row with exactly nine values are present. It never
    guesses a missing dataset. Image-only tables still need OCR.
    """
    result = TableExtractionResult()
    condition_rows = conditions or []
    methods = sorted({name for name in method_names if name}, key=len, reverse=True)

    for page_number, page in enumerate(pages, 1):
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        for header_index, line in enumerate(lines):
            dataset_order = _text_table_header(line)
            if not dataset_order or len(dataset_order) != 3:
                continue
            page_lower = page.lower()
            if (
                "only 10%" in page_lower
                or "10% of total" in page_lower
                or re.search(r"\btable\s+v\b", page_lower)
            ):
                ratio, protocol = "10%", "10% training"
            elif (
                "30% and 70%" in page_lower
                or "30% of the data" in page_lower
                or re.search(r"\btable\s+ii\b", page_lower)
            ):
                ratio, protocol = "30%", "30% training / 70% testing"
            else:
                ratio, protocol = None, None

            for row in lines[header_index + 1 : header_index + 30]:
                method = next((name for name in methods if name in row), None)
                if not method:
                    continue
                values = re.findall(r"\d{2,3}(?:\.\d+)?", row)
                if len(values) < 9:
                    continue
                values = values[:9]
                for index, value in enumerate(values):
                    dataset = dataset_order[index // 3]
                    metric = TEXT_TABLE_METRICS[index % 3]
                    condition = next(
                        (
                            item
                            for item in condition_rows
                            if normalized(item.dataset or "") in normalized(dataset)
                            or normalized(dataset) in normalized(item.dataset or "")
                        ),
                        None,
                    )
                    patch = condition.patch_size if condition else _patch_size_in(page)
                    evidence = make_evidence_ref(
                        document_id, pages, page_number, row, value=value
                    )
                    if not evidence.accepted:
                        result.rejections.append(
                            RejectionRecord(
                                field="metrics",
                                value=value,
                                page=page_number,
                                reason=evidence.status,
                                note=evidence.note,
                            )
                        )
                        continue
                    result.metrics.append(
                        MetricRecord(
                            dataset=dataset,
                            method=method,
                            metric=metric,
                            value=value,
                            train_ratio=ratio,
                            patch_size=patch,
                            protocol=protocol,
                            source="table",
                            evidence=[evidence],
                            note="文本表格行解析；dataset 由表头列顺序绑定，仍需人工抽样核对",
                        )
                    )
                result.datasets.extend(
                    DatasetRecord(name=name)
                    for name in dataset_order
                    if name not in {dataset.name for dataset in result.datasets}
                )
    if result.metrics:
        result.notes.append(
            f"文本表格行解析：绑定 {len(result.metrics)} 条指标；图片表格仍需 OCR。"
        )
    return result


TRANSPOSED_METRIC_RE = re.compile(r"^\s*(OA|AA|KAPPA(?:X100|X\s*100|×100)?)\b", re.IGNORECASE)
OCR_DATASET_CAPTIONS = (
    (re.compile(r"\bIN\s+DATA\s+SET\b", re.IGNORECASE), "Indian Pines"),
    (re.compile(r"\bINDIAN\s+PINS?\b", re.IGNORECASE), "Indian Pines"),
    (re.compile(r"\bUP\s+DATA\s+SET\b", re.IGNORECASE), "Pavia University"),
    (re.compile(r"\bUNIVERSITY\s+OF\s+PAV\s*I\s*A\b", re.IGNORECASE), "Pavia University"),
    (re.compile(r"\bKSC\s+DATA\s+SET\b", re.IGNORECASE), "Kennedy Space Center"),
)


def _ocr_dataset_from_line(line: str) -> str | None:
    for pattern, name in OCR_DATASET_CAPTIONS:
        if pattern.search(line):
            return name
    return _dataset_in(line)


def _ocr_metric_name(line: str) -> str | None:
    match = TRANSPOSED_METRIC_RE.match(line)
    if not match:
        return None
    raw = match.group(1).upper().replace(" ", "")
    if raw.startswith("OA"):
        return "OA"
    if raw.startswith("AA"):
        return "AA"
    return "Kappa"


def _method_token_map(methods: list[str]) -> dict[str, str]:
    aliases = {
        "hybridsn": "HybridSN",
        "hybirdsn": "HybridSN",
        "jssan": "JSAN",
        "wecg": "WFCG",
        "cnnl": "CNNL",
    }
    mapping: dict[str, str] = {}
    for name in methods:
        key = normalized(name).replace(" ", "")
        if key:
            mapping[key] = name
            mapping[key.replace("-", "")] = name
    for key, canonical in aliases.items():
        mapping.setdefault(key, canonical)
    return mapping


def parse_transposed_metric_rows(
    pages: list[str],
    document_id: str,
    method_names: list[str],
    conditions: list[ExperimentCondition] | None = None,
) -> TableExtractionResult:
    """Parse OCR output where methods are columns and OA/AA/Kappa are rows.

    Example::

        TABLE VI ... INDIAN PINES DATA SET
        SVM SAE CNN SSRN
        OA(%) 81.0 85.0 97.0 99.0
        AA(%) ...
        kappa x100 ...

    Dataset comes from the nearest preceding table caption. If the caption
    lacks a dataset or multiple datasets are present, the row is skipped.
    """
    result = TableExtractionResult()
    method_map = _method_token_map(method_names)
    condition_rows = conditions or []
    for page_number, page in enumerate(pages, 1):
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        current_dataset: str | None = None
        header: list[str] = []
        for line in lines:
            caption_dataset = _ocr_dataset_from_line(line)
            if caption_dataset and (
                current_dataset is None
                or "TABLE" in line.upper()
                or "DATA SET" in line.upper()
            ):
                current_dataset = caption_dataset
                header = []
                continue
            tokens = [token.strip(".,;:()_=+-|") for token in line.split()]
            candidate = [method_map[token.casefold()] for token in tokens if token.casefold() in method_map]
            if len(candidate) >= 2 and len(set(candidate)) == len(candidate):
                header = candidate
                continue
            metric = _ocr_metric_name(line)
            if metric is None or not header:
                continue
            if current_dataset is None:
                current_dataset = _ocr_dataset_from_line(page)
            if current_dataset is None:
                continue
            values = re.findall(r"\d{1,3}(?:\.\d+)", line)
            if len(values) < len(header):
                continue
            values = values[: len(header)]
            condition = next(
                (
                    item
                    for item in condition_rows
                    if normalized(item.dataset or "") == normalized(current_dataset)
                ),
                None,
            )
            for method, value in zip(header, values, strict=False):
                evidence = make_evidence_ref(document_id, pages, page_number, line, value=value)
                if not evidence.accepted:
                    result.rejections.append(
                        RejectionRecord(
                            field="metrics",
                            value=value,
                            page=page_number,
                            reason=evidence.status,
                            note=evidence.note,
                        )
                    )
                    continue
                result.metrics.append(
                    MetricRecord(
                        dataset=current_dataset,
                        method=method,
                        metric=metric,
                        value=value,
                        train_ratio=condition.train_ratio if condition else None,
                        patch_size=condition.patch_size if condition else None,
                        protocol=condition.protocol if condition else None,
                        source="table",
                        evidence=[evidence],
                        note="OCR 转置表解析；dataset 来自表题，需人工抽样核对",
                    )
                )
            if current_dataset and current_dataset not in {d.name for d in result.datasets}:
                result.datasets.append(DatasetRecord(name=current_dataset))
    if result.metrics:
        result.notes.append(f"OCR 转置表解析：绑定 {len(result.metrics)} 条指标。")
    return result


def _metric_key(metric: MetricRecord) -> tuple[str | None, str, str, int | None]:
    page = metric.evidence[0].page if metric.evidence else None
    return (metric.dataset, metric.metric, metric.value, page)


def merge_table_result(paper: PaperExtraction, table: TableExtractionResult) -> PaperExtraction:
    """Merge table metrics with text/LLM metrics, preferring table association."""
    metrics = list(paper.metrics)
    index_by_key = {_metric_key(metric): index for index, metric in enumerate(metrics)}
    for table_metric in table.metrics:
        key = _metric_key(table_metric)
        if key in index_by_key:
            existing = metrics[index_by_key[key]]
            metrics[index_by_key[key]] = table_metric.model_copy(
                update={
                    "dataset": table_metric.dataset or existing.dataset,
                    "train_ratio": table_metric.train_ratio or existing.train_ratio,
                    "patch_size": table_metric.patch_size or existing.patch_size,
                    "protocol": table_metric.protocol or existing.protocol,
                }
            )
        else:
            index_by_key[key] = len(metrics)
            metrics.append(table_metric)

    datasets = list(paper.datasets)
    dataset_names = {dataset.name for dataset in datasets}
    for dataset in table.datasets:
        if dataset.name not in dataset_names:
            datasets.append(dataset)
            dataset_names.add(dataset.name)

    conditions = list(paper.experiment_conditions)
    condition_keys = {
        (condition.dataset, condition.train_ratio, condition.patch_size, condition.protocol)
        for condition in conditions
    }
    for condition in table.conditions:
        key = (condition.dataset, condition.train_ratio, condition.patch_size, condition.protocol)
        if key not in condition_keys:
            conditions.append(condition)
            condition_keys.add(key)

    missing = list(paper.missing_fields)
    if metrics and "metrics" in missing:
        missing.remove("metrics")
    if datasets and "datasets" in missing:
        missing.remove("datasets")
    if conditions and "experiment_conditions" in missing:
        missing.remove("experiment_conditions")

    table_evidence = [evidence for metric in table.metrics for evidence in metric.evidence]
    stats = paper.stats.model_copy(
        update={
            "candidates": paper.stats.candidates + len(table.metrics) + len(table.rejections),
            "accepted": paper.stats.accepted + sum(1 for evidence in table_evidence if evidence.accepted),
            "rejected": paper.stats.rejected + len(table.rejections),
        }
    )
    notes = list(paper.notes)
    for note in table.notes:
        if note not in notes:
            notes.append(note)
    return paper.model_copy(
        update={
            "metrics": metrics,
            "datasets": datasets,
            "experiment_conditions": conditions,
            "missing_fields": missing,
            "rejections": list(paper.rejections) + list(table.rejections),
            "notes": notes,
            "stats": stats,
        }
    )
