# 评测记录

> 环境：Windows 11 / Python 3.12 / 单机。原则：只记录实际运行结果；未运行的指标明确写“未验证”。

## 1. 总览

| 指标 | 结果 | 来源 |
|---|---:|---|
| pytest | **103 passed** | `pytest -q` |
| coverage | **85%**（4461 / 678） | `pytest --cov` |
| ruff | **All checks passed** | `ruff check` |
| 合成夹具字段命中 | 20/20 | `scripts/evaluate_pipeline.py` |
| 合成夹具原文证据 | 23/23 | 同上 |
| GPT Researcher 本地 PDF 任务 | 10/10 | `scripts/evaluate_research.py` |
| GPT Researcher 网页任务 | 10/10 | 同上，Tavily + DeepSeek |
| 真实论文结构化抽取 | 见 §3 | 3 篇 PDF |
| 真实论文检索 | 见 §2 | 50 题 |
| Docker Compose | 本地构建/启动/worker 通过 | `docker compose` |

---

## 2. 真实论文检索

数据集：3 篇公开论文，50 道人工标注题。

- HybridSN：DOI `10.1109/LGRS.2019.2918719`
- SSRN：DOI `10.1109/TGRS.2017.2755542`
- WFCG：IEEE TIP 2022

标注字段：`document_id`、`gold_page`、`gold_answer`、`gold_quote`。  
评测只衡量检索/page 命中，不衡量回答语义。

### Answer-level Recall@5

| 模式 | R@1 | R@3 | R@5 | MRR@5 |
|---|---:|---:|---:|---:|
| BM25 | 32.0% | 58.0% | 68.0% | 0.465 |
| hash | 34.0% | 54.0% | 60.0% | 0.433 |
| bge-m3 vector | 54.0% | 70.0% | 78.0% | 0.630 |
| **bge-m3 hybrid** | 50.0% | 74.0% | **80.0%** | 0.611 |
| router | 44.0% | 62.0% | 70.0% | 0.540 |

### 严格 Page-level Recall@5

| 模式 | R@5 | MRR@5 |
|---|---:|---:|
| BM25 | 62.0% | 0.391 |
| hash | 52.0% | 0.354 |
| bge-m3 vector | 72.0% | 0.555 |
| **bge-m3 hybrid** | **72.0%** | 0.539 |
| router | 62.0% | 0.445 |

结论：

- `bge-m3 + hybrid` 是当前最佳组合（Answer-level 80.0%，page-level 72.0%）；
- page-level 仍有 28% 失败，集中在 SSRN 首页缩写、表格页切分；
- 50 题是自建集，不是公开 benchmark，不能外推。

详细失败分析：[RETRIEVAL_FAILURE_ANALYSIS.md](RETRIEVAL_FAILURE_ANALYSIS.md)。  
原始结果：[retrieval_runs.md](retrieval_runs.md) / [retrieval_runs.json](retrieval_runs.json)。

---

## 3. 结构化抽取

3 篇真实论文，人工标注为 gold：

| 字段 | 结果 |
|---|---:|
| title / year / venue / 主方法 | 3/3 |
| datasets | 9/9 |
| 指标数值 | 21/24 |
| 指标→数据集 | 21/24 |
| 实验条件 | 5/8 |
| 指标→训练比例/patch | 9/24 |
| 证据接受 | 271/277（97.8%） |

限制：

- 文本表 + Tesseract OCR 仍有误读和列错位；
- 指标→数据集绑定不完整；
- 不能据此做跨论文排名；
- 这是抽取子问题，不是“论文结论已验证”。

---

## 4. 引用核验

实现：

- 页级引用解析；
- `document_id + page + quote` 核验；
- claim-level 状态：`supported_quote`、`page_only`、`external_unchecked`、`no_citation`、`citation_failed`；
- 缺引用数值结论检测。

边界：

- 不验证语义蕴含；
- 外部链接不自动联网核验；
- 只说明“原文存在/值在原文中”，不说明“结论正确”。

---

## 5. 可靠性与并发

- SQLite WAL + `BEGIN IMMEDIATE` 原子领取；
- stale lock 超时恢复；
- queued 立即取消；
- running 协作取消，在阶段边界停止；
- 时间预算和成本预算；
- `finish_job` / `mark_done` 条件写入，避免 late worker 覆盖取消状态。

限制：running 取消不是硬杀进程；成本预算是上游返回后检查，不是调用前拦截。

---

## 6. 环境与限制

- 单机 SQLite，不是多租户或分布式系统；
- 网页任务需要 Tavily/网络；某些代理环境需要额外放行；
- Docker 只在本地验证，目标机器需要重新构建；
- OCR 依赖 Tesseract，非默认安装；
- LLM 成本统计依赖上游返回字段，不是完整账单。

---

## 7. 复现

```bash
pip install -r requirements-dev.txt
pytest -q
pytest -q --cov=spectrascholar --cov-report=term

python scripts/evaluate_retrieval.py --ocr --embedding hash
python scripts/evaluate_retrieval.py --ocr --embedding ollama
```

检索题集：[eval/research_eval.json](../eval/research_eval.json)。  
论文 PDF 不随仓库分发，需自行合法获取并放入 `workspace/papers/`。
