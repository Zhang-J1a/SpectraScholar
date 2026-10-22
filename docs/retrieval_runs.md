# 真实论文检索评测

- 生成时间：2026-10-22T11:14:50+00:00
- 问题数：50
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `vector` 使用 ollama:nomic-embed-text；hash 是另一条词法基线。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 32.00% | 58.00% | 68.00% | 0.4653 |
| hash | 34.00% | 54.00% | 60.00% | 0.4330 |
| vector | 30.00% | 60.00% | 70.00% | 0.4420 |
| hybrid | 46.00% | 66.00% | 72.00% | 0.5540 |
| router | 42.00% | 68.00% | 78.00% | 0.5487 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 24.00% | 50.00% | 62.00% | 0.3913 |
| hash | 24.00% | 50.00% | 52.00% | 0.3540 |
| vector | 24.00% | 46.00% | 64.00% | 0.3690 |
| hybrid | 38.00% | 54.00% | 70.00% | 0.4847 |
| router | 38.00% | 56.00% | 76.00% | 0.5007 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 75.00% | 0.4333 |
| condition | hash | 33.33% | 0.1625 |
| condition | vector | 75.00% | 0.4014 |
| condition | hybrid | 83.33% | 0.5236 |
| condition | router | 83.33% | 0.4917 |
| metadata | bm25 | 73.33% | 0.7000 |
| metadata | hash | 66.67% | 0.5444 |
| metadata | vector | 53.33% | 0.4167 |
| metadata | hybrid | 73.33% | 0.7000 |
| metadata | router | 73.33% | 0.7000 |
| metric | bm25 | 60.87% | 0.3290 |
| metric | hash | 69.57% | 0.5014 |
| metric | vector | 78.26% | 0.4797 |
| metric | hybrid | 65.22% | 0.4746 |
| metric | router | 78.26% | 0.4797 |

## 未命中示例（hybrid answer-level，前 10 条）

- `q037` SSRN 的作者是谁？（gold p.1）
- `q038` SSRN 的期刊卷期和起始页码是什么？（gold p.1）

