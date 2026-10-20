"""Multi-paper comparison and Markdown export (P1-B).

The central rule is that OA/AA/Kappa numbers are only put into the same
comparable group when dataset, metric, training ratio and patch size all match.
Even then the report says that split protocol and random seeds still need a
human check.  Missing conditions are shown as "不可比", never silently ranked.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import uuid4

from .schemas import (
    ComparabilityIssue,
    ComparisonResponse,
    DatasetCell,
    DatasetRow,
    MethodRow,
    MetricRow,
    PaperExtraction,
    PaperProfile,
)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _numeric(value: str) -> float | None:
    match = re.search(r"\d{1,3}(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _first_method(paper: PaperExtraction) -> str | None:
    return paper.methods[0].name if paper.methods else None


def _method_rows(papers: list[PaperExtraction]) -> list[MethodRow]:
    rows: list[MethodRow] = []
    for paper in papers:
        graph_kinds = _unique([graph.kind for graph in paper.graph_constructions])
        for method in paper.methods:
            statuses = [evidence.status for evidence in method.evidence]
            rows.append(
                MethodRow(
                    document_id=paper.document_id,
                    filename=paper.filename,
                    method=method.name,
                    family=method.family,
                    graph_construction=_unique(method.graph_construction + graph_kinds),
                    evidence_status=statuses[0] if statuses else "unverified",
                )
            )
    return rows


def _dataset_matrix(papers: list[PaperExtraction]) -> list[DatasetRow]:
    names = _unique([dataset.name for paper in papers for dataset in paper.datasets])
    rows: list[DatasetRow] = []
    for name in names:
        cells = []
        for paper in papers:
            pages = sorted(
                {
                    evidence.page
                    for dataset in paper.datasets
                    if dataset.name == name
                    for evidence in dataset.evidence
                    if evidence.page is not None
                }
            )
            cells.append(
                DatasetCell(document_id=paper.document_id, present=bool(pages), pages=[int(page) for page in pages])
            )
        rows.append(DatasetRow(dataset=name, cells=cells))
    return rows


def _missing_condition_reasons(paper: PaperExtraction, metric) -> list[str]:
    reasons: list[str] = []
    if not metric.dataset:
        reasons.append("指标未关联到具体数据集")
    if not metric.train_ratio:
        reasons.append("缺少训练样本比例")
    if not metric.patch_size:
        reasons.append("缺少输入补丁尺寸")
    if not metric.protocol:
        reasons.append("未记录数据划分/实验协议")
    if not any(evidence.accepted for evidence in metric.evidence):
        reasons.append("指标缺少通过核验的原文证据")
    return reasons


def _metric_rows(papers: list[PaperExtraction]) -> tuple[list[MetricRow], list[ComparabilityIssue]]:
    rows: list[MetricRow] = []
    for paper in papers:
        for metric in paper.metrics:
            missing = _missing_condition_reasons(paper, metric)
            evidence_status = metric.evidence[0].status if metric.evidence else "unverified"
            complete = not missing
            group = (
                f"{metric.dataset}|{metric.metric}|{metric.train_ratio}|{metric.patch_size}"
                if complete
                else None
            )
            rows.append(
                MetricRow(
                    document_id=paper.document_id,
                    filename=paper.filename,
                    method=_first_method(paper),
                    dataset=metric.dataset,
                    metric=metric.metric,
                    value=metric.value,
                    train_ratio=metric.train_ratio,
                    patch_size=metric.patch_size,
                    protocol=metric.protocol,
                    evidence_status=evidence_status,
                    comparable_group=group,
                    comparable=False,
                    reason="；".join(missing) if missing else None,
                )
            )

    # Only rank rows that share every recorded condition and come from >= 2 papers.
    groups: dict[str, list[MetricRow]] = {}
    for row in rows:
        if row.comparable_group:
            groups.setdefault(row.comparable_group, []).append(row)
    for members in groups.values():
        documents = {member.document_id for member in members}
        if len(documents) < 2:
            for member in members:
                member.reason = "没有其他论文在完全相同的条件下报告该指标，无法排名"
            continue
        scored = [(member, _numeric(member.value)) for member in members]
        scored = [(member, value) for member, value in scored if value is not None]
        for member, value in scored:
            member.comparable = True
            member.rank_in_group = 1 + sum(1 for _, other in scored if other is not None and other > value)
            member.reason = (
                "数据集、指标、训练比例与补丁尺寸一致；仍需核对数据划分、随机种子与是否使用相同评估代码"
            )

    issues: list[ComparabilityIssue] = []
    no_dataset = [row.document_id for row in rows if not row.dataset]
    if no_dataset:
        issues.append(
            ComparabilityIssue(
                code="metric_dataset_missing",
                message="部分指标没有可靠关联到数据集，不能与其他论文的数值并列比较。",
                document_ids=sorted(set(no_dataset)),
            )
        )
    no_ratio = [row.document_id for row in rows if row.dataset and not row.train_ratio]
    if no_ratio:
        issues.append(
            ComparabilityIssue(
                code="train_ratio_missing",
                message="部分指标缺少训练样本比例；不同比例下的 OA/AA/Kappa 不能直接用于模型排名。",
                document_ids=sorted(set(no_ratio)),
            )
        )
    no_patch = [row.document_id for row in rows if row.dataset and not row.patch_size]
    if no_patch:
        issues.append(
            ComparabilityIssue(
                code="patch_size_missing",
                message="输入补丁尺寸缺失，空间上下文不同也会影响指标可比性。",
                document_ids=sorted(set(no_patch)),
            )
        )
    # Same dataset+metric but different recorded protocols.
    buckets: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        if row.dataset:
            buckets.setdefault((row.dataset, row.metric), set()).add(row.train_ratio or "未注明")
    for (dataset, metric), ratios in buckets.items():
        if len(ratios) > 1:
            issues.append(
                ComparabilityIssue(
                    code="protocol_mismatch",
                    message=f"{dataset} 的 {metric} 在不同训练比例下被报告（{', '.join(sorted(ratios))}），不可直接排名。",
                    dataset=dataset,
                    metric=metric,
                )
            )
    if not rows:
        issues.append(
            ComparabilityIssue(
                code="no_metrics_extracted",
                message="未抽取到可定位的 OA/AA/Kappa 指标；系统不会补造数值。",
            )
        )
    return rows, issues


def _profile(paper: PaperExtraction) -> PaperProfile:
    title = paper.metadata.title.value
    authors = paper.metadata.authors.value
    year = paper.metadata.year.value
    methods = _unique([method.name for method in paper.methods])
    families = _unique([method.family for method in paper.methods if method.family])
    datasets = _unique([dataset.name for dataset in paper.datasets])
    metrics_summary = [
        f"{metric.dataset or '数据集未注明'} {metric.metric}={metric.value}"
        + (f"（训练比例 {metric.train_ratio}）" if metric.train_ratio else "")
        for metric in paper.metrics
    ]

    strengths: list[str] = []
    if methods and all(
        any(evidence.accepted for evidence in method.evidence) for method in paper.methods
    ):
        strengths.append("方法名称均能定位到 PDF 原文")
    if datasets:
        strengths.append(f"报告了 {len(datasets)} 个可在原文定位的数据集")
    if paper.metrics:
        strengths.append(f"报告了 {len(paper.metrics)} 条可定位的实验指标")
    if any(condition.train_ratio for condition in paper.experiment_conditions):
        strengths.append("记录了训练样本比例等实验条件")
    if paper.graph_constructions:
        strengths.append(
            "描述了图构建方式：" + "、".join(_unique([graph.kind for graph in paper.graph_constructions]))
        )

    limitations: list[str] = []
    if paper.metadata.authors.missing:
        limitations.append("作者信息未可靠抽取")
    if paper.metadata.year.missing:
        limitations.append("出版年份未可靠抽取")
    if not metrics_summary:
        limitations.append("未抽取到 OA/AA/Kappa，无法参与定量比较")
    if any(not metric.dataset for metric in paper.metrics):
        limitations.append("部分指标未关联到数据集")
    if any(not metric.train_ratio for metric in paper.metrics):
        limitations.append("部分指标缺少训练样本比例")
    if "GNN" in families and not paper.graph_constructions:
        limitations.append("GNN 论文但未提取到 KNN/RBF/静态/动态图等构建描述")
    if paper.extraction_mode == "heuristic":
        limitations.append("当前离线模式不解析表格结构，指标关联需要人工复核")
    if not paper.has_text:
        limitations.append("PDF 未提取到可用文本，可能需要 OCR")

    scenarios: list[str] = []
    if "GNN" in families:
        scenarios.append("适合考察图结构建模、邻接关系构建在空谱分类中的作用")
    if "Transformer" in families:
        scenarios.append("适合考察长程依赖与全局上下文建模")
    if "CNN" in families:
        scenarios.append("适合作为局部空谱特征提取的基线对照")
    if datasets:
        scenarios.append(f"在这些数据集上有实验记录，可优先做同数据集复现对照：{', '.join(datasets)}")
    if not scenarios:
        scenarios.append("证据不足，无法给出适用场景建议")
    scenarios.append("以上为规则生成的阅读提示，不是论文作者的结论")

    return PaperProfile(
        document_id=paper.document_id,
        filename=paper.filename,
        title=title,
        authors=authors,
        year=year,
        methods=methods,
        model_families=families,
        datasets=datasets,
        metrics_summary=metrics_summary,
        strengths=strengths,
        limitations=limitations,
        applicable_scenarios=scenarios,
        missing_fields=paper.missing_fields,
    )


def _quote_for_citation(evidence) -> str | None:
    quote = evidence.quote
    if not quote:
        return None
    collapsed = " ".join(quote.split())
    if '"' in collapsed or "|" in collapsed or len(collapsed) > 500:
        return None
    return collapsed


def _evidence_appendix(papers: list[PaperExtraction]) -> list[str]:
    lines = ["## 证据附录", "", "每条本地引用均可用下方页码与原文片段复核。", ""]
    for paper in papers:
        lines += [f"### {paper.filename}", ""]
        lines.append(f"- 文档 ID：`{paper.document_id}`")
        lines.append(
            f"- 抽取模式：`{paper.extraction_mode}`；缺失字段：{', '.join(paper.missing_fields) or '无'}"
        )
        lines.append("")
        entries: list[tuple[str, object]] = []
        for name in ("title", "authors", "year", "venue"):
            field = getattr(paper.metadata, name)
            for evidence in field.evidence:
                entries.append((f"metadata.{name}", evidence))
        for method in paper.methods:
            for evidence in method.evidence:
                entries.append((f"method:{method.name}", evidence))
        for dataset in paper.datasets:
            for evidence in dataset.evidence:
                entries.append((f"dataset:{dataset.name}", evidence))
        for graph in paper.graph_constructions:
            for evidence in graph.evidence:
                entries.append((f"graph:{graph.kind}", evidence))
        for condition in paper.experiment_conditions:
            for evidence in condition.evidence:
                entries.append(("condition", evidence))
        for metric in paper.metrics:
            label = f"metric:{metric.metric}={metric.value}"
            for evidence in metric.evidence:
                entries.append((label, evidence))
        if not entries:
            lines.append("- 未获得可核验的原文证据。")
            lines.append("")
            continue
        lines += ["| 字段 | 页码 | 状态 | 引用 |", "|---|---|---|---|"]
        for field, evidence in entries[:40]:
            if evidence.page is None:
                continue
            quote = _quote_for_citation(evidence)
            if quote:
                citation = f'[[doc:{paper.document_id} p.{evidence.page} "{quote}"]]'
            else:
                citation = f"[[doc:{paper.document_id} p.{evidence.page}]]"
            lines.append(
                f"| {_cell(field)} | {evidence.page} | {evidence.status} | {_cell(citation)} |"
            )
        if len(entries) > 40:
            lines.append(f"| …… | | | 其余 {len(entries) - 40} 条已省略 |")
        lines.append("")
    return lines


def build_markdown(
    papers: list[PaperExtraction],
    profiles: list[PaperProfile],
    method_rows: list[MethodRow],
    dataset_matrix: list[DatasetRow],
    metric_rows: list[MetricRow],
    issues: list[ComparabilityIssue],
    extraction_mode: str,
    generated_at: str,
) -> str:
    lines: list[str] = [
        "# 多论文结构化对比报告",
        "",
        f"- 生成时间（UTC）：{generated_at}",
        f"- 抽取模式：`{extraction_mode}`",
        f"- 论文数量：{len(papers)}",
        "",
        "> **可比性声明**：证据核验只证明引文出现在指定 PDF 页码，不代表事实语义正确。"
        "只有数据集、指标、训练比例和补丁尺寸全部一致的数值才会被放入同一可比组；"
        "即使如此，数据划分、随机种子和评估代码仍可能不同。训练比例缺失的数值不参与排名。",
        "",
        "## 1. 论文概览",
        "",
        "| 论文 | 标题 | 年份 | 方法 | 模型家族 | 数据集 | 指标数 |",
        "|---|---|---|---|---|---|---|",
    ]
    for profile in profiles:
        lines.append(
            "| {filename} | {title} | {year} | {methods} | {families} | {datasets} | {metrics} |".format(
                filename=_cell(profile.filename),
                title=_cell(profile.title or "未抽取"),
                year=_cell(profile.year or "未抽取"),
                methods=_cell(", ".join(profile.methods) or "未抽取"),
                families=_cell(", ".join(profile.model_families) or "未判定"),
                datasets=_cell(", ".join(profile.datasets) or "未抽取"),
                metrics=len(profile.metrics_summary),
            )
        )

    lines += ["", "## 2. 研究方法对比", ""]
    if method_rows:
        lines += ["| 论文 | 方法/模型 | 家族 | 图构建 | 证据状态 |", "|---|---|---|---|---|"]
        for row in method_rows:
            lines.append(
                f"| {_cell(row.filename)} | {_cell(row.method)} | {_cell(row.family or '未判定')} | "
                f"{_cell(', '.join(row.graph_construction) or '未描述')} | {row.evidence_status} |"
            )
    else:
        lines.append("未抽取到方法名称；系统没有根据领域常识补全。")

    lines += ["", "## 3. 数据集使用矩阵", ""]
    if dataset_matrix:
        header = "| 数据集 | " + " | ".join(_cell(paper.filename) for paper in papers) + " |"
        separator = "|---|" + "---|" * len(papers)
        lines += [header, separator]
        for row in dataset_matrix:
            cells = []
            for cell in row.cells:
                cells.append("✓" + (f" p.{','.join(map(str, cell.pages))}" if cell.present else ""))
            lines.append(f"| {_cell(row.dataset)} | " + " | ".join(cells) + " |")
    else:
        lines.append("未抽取出数据集名称。")

    lines += ["", "## 4. 实验指标与可比性", ""]
    if metric_rows:
        lines += [
            "| 论文 | 方法 | 数据集 | 指标 | 数值 | 训练比例 | 补丁 | 证据 | 可比 | 组内排名 | 说明 |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for row in metric_rows:
            lines.append(
                f"| {_cell(row.filename)} | {_cell(row.method or '未提取')} | {_cell(row.dataset or '未注明')} | "
                f"{_cell(row.metric)} | {_cell(row.value)} | {_cell(row.train_ratio or '未注明')} | "
                f"{_cell(row.patch_size or '未注明')} | {row.evidence_status} | "
                f"{'是' if row.comparable else '否'} | {row.rank_in_group or '-'} | {_cell(row.reason or '')} |"
            )
    else:
        lines.append("未抽取到可核验的 OA/AA/Kappa 指标。")

    lines += ["", "### 不可比项与风险提示", ""]
    if issues:
        for issue in issues:
            lines.append(f"- **{issue.code}**：{issue.message}")
    else:
        lines.append("- 未发现跨论文条件冲突；仍需人工核对实验协议。")

    lines += ["", "## 5. 单篇论文画像", ""]
    for profile in profiles:
        lines += [f"### {profile.filename}", ""]
        if profile.title:
            lines.append(f"- 标题：{profile.title}")
        if profile.authors:
            lines.append(f"- 作者：{profile.authors}")
        if profile.year:
            lines.append(f"- 年份：{profile.year}")
        lines.append(f"- 优势（有证据支撑的事实）：{'；'.join(profile.strengths) or '无'}")
        lines.append(f"- 局限/缺失：{'；'.join(profile.limitations) or '无'}")
        lines.append(f"- 适用场景：{'；'.join(profile.applicable_scenarios)}")
        lines.append("")

    lines += ["## 6. 方法与结论的人工复核清单", ""]
    lines += [
        "- [ ] 核对每个数值对应的数据划分方式（随机/固定/地理划分）与随机种子。",
        "- [ ] 核对 OA/AA/Kappa 是否在同一评估代码、同一类别集合下计算。",
        "- [ ] 核对训练样本比例与输入补丁尺寸是否确实对应表中数值。",
        "- [ ] 对表格中的数字回到 PDF 原页人工确认，不要只依赖文本抽取。",
        "- [ ] 若论文使用不同数据集，不要用跨数据集均值或单一 OA 排名。",
        "",
    ]
    lines += _evidence_appendix(papers)
    return "\n".join(lines)


def build_comparison(
    papers: list[PaperExtraction],
    *,
    extraction_mode: str,
    language: str = "zh",
) -> ComparisonResponse:
    profiles = [_profile(paper) for paper in papers]
    method_rows = _method_rows(papers)
    dataset_matrix = _dataset_matrix(papers)
    metric_rows, issues = _metric_rows(papers)
    generated_at = _utcnow()
    markdown = build_markdown(
        papers,
        profiles,
        method_rows,
        dataset_matrix,
        metric_rows,
        issues,
        extraction_mode,
        generated_at,
    )
    return ComparisonResponse(
        comparison_id=str(uuid4()),
        papers=papers,
        profiles=profiles,
        method_rows=method_rows,
        dataset_matrix=dataset_matrix,
        metric_rows=metric_rows,
        comparability_issues=issues,
        extraction_mode=extraction_mode,
        generated_at=generated_at,
        markdown=markdown,
    )
