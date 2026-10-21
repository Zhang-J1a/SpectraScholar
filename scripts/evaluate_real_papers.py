"""P4.3: real-paper extraction evaluation on manually labeled PDFs.

Runs the production extraction service in heuristic and LLM modes on three
real papers, then compares title/year/venue, methods, datasets, experimental
conditions and metric rows against ``eval/real_papers.labels.json``.

This measures extraction fidelity, not paper quality. LLM mode makes real
DeepSeek calls (requires .env).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / ".evaluation-real-papers" / "workspace"
LABELS = ROOT / "eval" / "real_papers.labels.json"
sys.path.insert(0, str(ROOT))

os.environ["WORKSPACE_DIR"] = str(WORKSPACE)
os.environ["EXTRACTOR_BACKEND"] = "llm"
os.environ["TABLE_EXTRACTION_ENABLED"] = "1"
if "--ocr" in sys.argv:
    os.environ["OCR_ENABLED"] = "1"
os.environ.pop("SPECTRASCHOLAR_SKIP_DOTENV", None)

from spectrascholar.extraction.service import evidence_counts, extract_document  # noqa: E402

ALIASES = {
    "indian pines": ("indian pines", "indian pine", "ip"),
    "pavia university": ("pavia university", "university of pavia", "pavia"),
    "salinas scene": ("salinas scene", "salinas"),
    "kennedy space center": ("kennedy space center", "ksc"),
    "whu-hi-honghu": ("whu-hi-honghu", "whu-hi", "honghu"),
}
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def norm(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    text = re.sub(r"[^a-z0-9%.]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def dataset_key(name: str | None) -> str | None:
    value = norm(name)
    if not value:
        return None
    for key, aliases in ALIASES.items():
        if any(alias == value or alias in value for alias in aliases):
            return key
    return value


def parse_number(value: str | None) -> float | None:
    if not value:
        return None
    match = NUMBER_RE.search(value.replace(",", ""))
    return float(match.group(0)) if match else None


def metric_value_match(expected: str, actual: str) -> bool:
    want = parse_number(expected)
    got = parse_number(actual)
    if want is None or got is None:
        return False
    if abs(want - got) <= 0.011:
        return True
    # Kappa is sometimes stored as 0.997 and sometimes as 99.7.
    if want > 1 and got <= 1:
        return abs(want - got * 100) <= 0.011
    if want <= 1 and got > 1:
        return abs(want * 100 - got) <= 0.011
    return False


def field_hit(expected: str | None, actual: str | None) -> bool:
    want, got = norm(expected), norm(actual)
    if not want or not got:
        return False
    return want == got or want in got or got in want


def patch_match(expected: str | None, actual: str | None) -> bool:
    """Accept 7x7 for an extracted 7x7x200 input volume, but not a wrong patch."""
    want, got = norm(expected), norm(actual)
    if not want:
        return True
    if not got:
        return False
    return got == want or got.startswith(f"{want}x")


def paper_scores(label: dict, paper) -> dict:
    extracted_methods = [method.name for method in paper.methods]
    extracted_datasets = [dataset.name for dataset in paper.datasets]
    extracted_conditions = [
        {
            "dataset": dataset_key(condition.dataset),
            "train_ratio": norm(condition.train_ratio).replace("%", ""),
            "patch_size": norm(condition.patch_size),
        }
        for condition in paper.experiment_conditions
    ]

    fields: dict[str, list[int]] = {
        "title": [0, 1],
        "year": [0, 1],
        "venue": [0, 1],
        "primary_method": [0, 1],
        "datasets": [0, 0],
        "conditions": [0, 0],
    }
    fields["title"][0] = int(field_hit(label["title"], paper.metadata.title.value))
    fields["year"][0] = int(str(label["year"]) == str(paper.metadata.year.value or ""))
    fields["venue"][0] = int(field_hit(label["venue"], paper.metadata.venue.value))
    fields["primary_method"][0] = int(
        any(field_hit(label["primary_method"], name) for name in extracted_methods)
    )

    for expected_dataset in label["datasets"]:
        fields["datasets"][1] += 1
        if any(dataset_key(name) == dataset_key(expected_dataset) for name in extracted_datasets):
            fields["datasets"][0] += 1

    for condition in label["conditions"]:
        fields["conditions"][1] += 1
        target_dataset = dataset_key(condition["dataset"])
        target_ratio = norm(condition["train_ratio"]).replace("%", "")
        target_patch = norm(condition.get("patch_size"))
        for actual in extracted_conditions:
            if actual["dataset"] != target_dataset:
                continue
            if actual["train_ratio"] != target_ratio:
                continue
            if target_patch and not patch_match(target_patch, actual["patch_size"]):
                continue
            fields["conditions"][0] += 1
            break

    metric_value_hits = 0
    association_hits = 0
    conditioned_hits = 0
    for expected in label["metrics"]:
        metric_value_hits += int(
            any(
                norm(metric.metric) == norm(expected["metric"])
                and metric_value_match(expected["value"], metric.value)
                for metric in paper.metrics
            )
        )
        association_hits += int(
            any(
                norm(metric.metric) == norm(expected["metric"])
                and metric_value_match(expected["value"], metric.value)
                and dataset_key(metric.dataset) == dataset_key(expected["dataset"])
                for metric in paper.metrics
            )
        )
        conditioned_hits += int(
            any(
                norm(metric.metric) == norm(expected["metric"])
                and metric_value_match(expected["value"], metric.value)
                and dataset_key(metric.dataset) == dataset_key(expected["dataset"])
                and norm(metric.train_ratio).replace("%", "")
                == norm(expected.get("train_ratio")).replace("%", "")
                and patch_match(expected.get("patch_size"), metric.patch_size)
                for metric in paper.metrics
            )
        )

    evidence = evidence_counts(paper)
    return {
        "fields": fields,
        "metrics": {
            "value": [metric_value_hits, len(label["metrics"])],
            "dataset_association": [association_hits, len(label["metrics"])],
            "conditioned": [conditioned_hits, len(label["metrics"])],
        },
        "evidence": evidence,
        "extracted": {
            "title": paper.metadata.title.value,
            "year": paper.metadata.year.value,
            "venue": paper.metadata.venue.value,
            "methods": extracted_methods[:15],
            "datasets": extracted_datasets[:15],
            "conditions": len(paper.experiment_conditions),
            "metrics": len(paper.metrics),
            "rejections": len(paper.rejections),
        },
    }


def aggregate(results: list[dict]) -> dict:
    totals: dict[str, list[int]] = {}
    for result in results:
        for section in ("fields", "metrics"):
            for key, (hit, total) in result[section].items():
                bucket = totals.setdefault(f"{section}.{key}", [0, 0])
                bucket[0] += hit
                bucket[1] += total
    out = {}
    for key, (hit, total) in totals.items():
        out[key] = {"hit": hit, "total": total, "accuracy": round(hit / total, 4) if total else None}
    out["evidence_acceptance"] = {
        "accepted": sum(result["evidence"]["evidence_verified"] for result in results),
        "total": sum(
            result["evidence"]["evidence_verified"] + result["evidence"]["rejected"]
            for result in results
        ),
    }
    accepted = out["evidence_acceptance"]["accepted"]
    total = out["evidence_acceptance"]["total"]
    out["evidence_acceptance"]["rate"] = round(accepted / total, 4) if total else None
    return out


async def run_mode(mode: str, labels: dict) -> dict:
    results = []
    for label in labels["papers"]:
        path = ROOT / "workspace" / "papers" / label["filename"]
        print(f"[{mode}] {label['id']} ...", flush=True)
        paper = await extract_document(label["id"], label["filename"], path, mode=mode)
        result = {"id": label["id"], "filename": label["filename"], **paper_scores(label, paper)}
        results.append(result)
        print(
            f"  methods={len(result['extracted']['methods'])} "
            f"datasets={len(result['extracted']['datasets'])} "
            f"metrics={result['extracted']['metrics']}",
            flush=True,
        )
    return {"mode": mode, "papers": results, "summary": aggregate(results)}


def print_summary(payload: dict) -> None:
    print(f"\n## mode={payload['mode']}")
    for key, value in payload["summary"].items():
        if key == "evidence_acceptance":
            print(
                f"  evidence acceptance: {value['accepted']}/{value['total']} "
                f"({value['rate']})"
            )
        else:
            print(f"  {key}: {value['hit']}/{value['total']} ({value['accuracy']})")


def main() -> int:
    labels = json.loads(LABELS.read_text(encoding="utf-8"))
    outputs = {}
    for mode in ("heuristic", "llm"):
        outputs[mode] = asyncio.run(run_mode(mode, labels))
        print_summary(outputs[mode])
    payload = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": "real_papers",
        "papers": [label["id"] for label in labels["papers"]],
        "excluded": [
            "c009fcebc686498bb0609d970647e316.pdf (Chinese HyperAE reading notes)",
            "d60d17dea771411ca265badcc5ebc3f2.pdf (Chinese F2HNN reading notes)",
        ],
        "labels": str(LABELS.relative_to(ROOT)),
        "modes": outputs,
        "note": (
            "人工标注 3 篇真实论文的 24 条指标；只评测抽取保真度，不评测论文结论正确性。"
            "heuristic/LLM 使用同一批 PDF；LLM 会产生真实 API 费用。"
        ),
    }
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "real_paper_runs.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# 真实论文抽取评测",
        "",
        f"- 生成时间：{payload['generated_at']}",
        "- 语料：3 篇英文原论文 + 2 份中文精读笔记（后者排除）",
        "- 标注：24 条指标、8 个实验条件、9 个数据集字段",
        "",
        "| 模式 | title | year | venue | method | datasets | conditions | metric value | dataset+metric | conditioned | evidence |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for mode, data in outputs.items():
        summary = data["summary"]
        lines.append(
            f"| {mode} | {summary['fields.title']['hit']}/{summary['fields.title']['total']} | "
            f"{summary['fields.year']['hit']}/{summary['fields.year']['total']} | "
            f"{summary['fields.venue']['hit']}/{summary['fields.venue']['total']} | "
            f"{summary['fields.primary_method']['hit']}/{summary['fields.primary_method']['total']} | "
            f"{summary['fields.datasets']['hit']}/{summary['fields.datasets']['total']} | "
            f"{summary['fields.conditions']['hit']}/{summary['fields.conditions']['total']} | "
            f"{summary['metrics.value']['hit']}/{summary['metrics.value']['total']} | "
            f"{summary['metrics.dataset_association']['hit']}/{summary['metrics.dataset_association']['total']} | "
            f"{summary['metrics.conditioned']['hit']}/{summary['metrics.conditioned']['total']} | "
            f"{summary['evidence_acceptance']['accepted']}/{summary['evidence_acceptance']['total']} |"
        )
    lines += [
        "",
        "## 关键解释",
        "",
        "- `metric value`：只要求指标名和数值命中，不要求绑定数据集；",
        "- `dataset+metric`：要求同一指标还绑定到正确数据集；",
        "- `conditioned`：再要求训练比例/ patch size 一致；",
        "- `evidence`：抽取器接受的逐字证据 /（接受 + 拒绝）；",
        "- 这是抽取保真度评测，不代表论文结论正确性，也不代表跨论文可比性。",
        "",
        "原始结果：[`real_paper_runs.json`](real_paper_runs.json)。",
        "",
    ]
    (docs / "real_paper_runs.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwritten: {docs / 'real_paper_runs.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
