# 真实论文检索评测

- 生成时间：2026-10-22T11:38:38+00:00
- 问题数：50
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `vector` 使用 ollama:bge-m3；hash 是另一条词法基线。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 32.00% | 58.00% | 68.00% | 0.4653 |
| hash | 34.00% | 54.00% | 60.00% | 0.4330 |
| vector | 54.00% | 70.00% | 78.00% | 0.6300 |
| hybrid | 50.00% | 74.00% | 80.00% | 0.6107 |
| router | 44.00% | 62.00% | 70.00% | 0.5400 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 24.00% | 50.00% | 62.00% | 0.3913 |
| hash | 24.00% | 50.00% | 52.00% | 0.3540 |
| vector | 48.00% | 62.00% | 72.00% | 0.5550 |
| hybrid | 46.00% | 60.00% | 72.00% | 0.5393 |
| router | 36.00% | 52.00% | 62.00% | 0.4450 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 75.00% | 0.4333 |
| condition | hash | 33.33% | 0.1625 |
| condition | vector | 83.33% | 0.6806 |
| condition | hybrid | 83.33% | 0.5833 |
| condition | router | 83.33% | 0.6806 |
| metadata | bm25 | 73.33% | 0.7000 |
| metadata | hash | 66.67% | 0.5444 |
| metadata | vector | 100.00% | 1.0000 |
| metadata | hybrid | 100.00% | 1.0000 |
| metadata | router | 73.33% | 0.7000 |
| metric | bm25 | 60.87% | 0.3290 |
| metric | hash | 69.57% | 0.5014 |
| metric | vector | 60.87% | 0.3623 |
| metric | hybrid | 65.22% | 0.3710 |
| metric | router | 60.87% | 0.3623 |

## 未命中示例（hybrid answer-level，前 10 条）

- `q020` SSRN 在 University of Pavia、10% 训练比例下的 Kappa 是多少？（gold p.7）

