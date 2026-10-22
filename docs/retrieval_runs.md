# 真实论文检索评测

- 生成时间：2026-10-22T10:19:02+00:00
- 问题数：30
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `vector` 使用 ollama:nomic-embed-text；hash 是另一条词法基线。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 23.33% | 50.00% | 63.33% | 0.3839 |
| hash | 33.33% | 56.67% | 66.67% | 0.4511 |
| vector | 30.00% | 56.67% | 70.00% | 0.4356 |
| hybrid | 40.00% | 60.00% | 63.33% | 0.4917 |
| router | 36.67% | 63.33% | 73.33% | 0.5011 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 0.00% | 30.00% | 46.67% | 0.1717 |
| hash | 6.67% | 36.67% | 43.33% | 0.2039 |
| vector | 20.00% | 36.67% | 50.00% | 0.2928 |
| hybrid | 20.00% | 30.00% | 40.00% | 0.2567 |
| router | 20.00% | 36.67% | 53.33% | 0.3011 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 66.67% | 0.1500 |
| condition | hash | 33.33% | 0.0833 |
| condition | vector | 33.33% | 0.0833 |
| condition | hybrid | 33.33% | 0.1111 |
| condition | router | 33.33% | 0.0833 |
| metadata | bm25 | 77.78% | 0.6296 |
| metadata | hash | 77.78% | 0.6389 |
| metadata | vector | 66.67% | 0.4204 |
| metadata | hybrid | 77.78% | 0.6111 |
| metadata | router | 77.78% | 0.6389 |
| metric | bm25 | 55.56% | 0.3000 |
| metric | hash | 66.67% | 0.4185 |
| metric | vector | 77.78% | 0.5019 |
| metric | hybrid | 61.11% | 0.4954 |
| metric | router | 77.78% | 0.5019 |

## 未命中示例（hybrid answer-level，前 10 条）

无未命中。

