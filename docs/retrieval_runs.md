# 真实论文检索评测

- 生成时间：2026-10-22T10:32:19+00:00
- 问题数：30
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `vector` 使用 ollama:nomic-embed-text；hash 是另一条词法基线。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 30.00% | 50.00% | 63.33% | 0.4283 |
| hash | 33.33% | 60.00% | 66.67% | 0.4539 |
| vector | 33.33% | 60.00% | 70.00% | 0.4678 |
| hybrid | 50.00% | 60.00% | 63.33% | 0.5417 |
| router | 36.67% | 66.67% | 73.33% | 0.5039 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 20.00% | 40.00% | 56.67% | 0.3383 |
| hash | 23.33% | 56.67% | 60.00% | 0.3789 |
| vector | 26.67% | 46.67% | 60.00% | 0.3761 |
| hybrid | 40.00% | 50.00% | 60.00% | 0.4567 |
| router | 36.67% | 56.67% | 70.00% | 0.4761 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 66.67% | 0.1500 |
| condition | hash | 33.33% | 0.0833 |
| condition | vector | 33.33% | 0.0833 |
| condition | hybrid | 33.33% | 0.1111 |
| condition | router | 33.33% | 0.0833 |
| metadata | bm25 | 77.78% | 0.7778 |
| metadata | hash | 77.78% | 0.6481 |
| metadata | vector | 66.67% | 0.5278 |
| metadata | hybrid | 77.78% | 0.7778 |
| metadata | router | 77.78% | 0.6481 |
| metric | bm25 | 55.56% | 0.3000 |
| metric | hash | 66.67% | 0.4185 |
| metric | vector | 77.78% | 0.5019 |
| metric | hybrid | 61.11% | 0.4954 |
| metric | router | 77.78% | 0.5019 |

## 未命中示例（hybrid answer-level，前 10 条）

无未命中。

