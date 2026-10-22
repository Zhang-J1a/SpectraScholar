# 真实论文检索评测

- 生成时间：2026-10-22T09:21:27+00:00
- 问题数：30
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `vector` 使用当前 embedding backend（本次 `ollama:nomic-embed-text`，768 维）。
- hash 是另一条词法基线，不能把 Ollama 结果写成“语义提升”。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 10.00% | 30.00% | 36.67% | 0.2056 |
| vector | 16.67% | 30.00% | 43.33% | 0.2539 |
| hybrid | 23.33% | 33.33% | 36.67% | 0.2861 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 0.00% | 23.33% | 33.33% | 0.1194 |
| vector | 10.00% | 13.33% | 30.00% | 0.1511 |
| hybrid | 10.00% | 13.33% | 23.33% | 0.1361 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 33.33% | 0.0833 |
| condition | vector | 33.33% | 0.0833 |
| condition | hybrid | 33.33% | 0.1111 |
| metadata | bm25 | 44.44% | 0.2963 |
| metadata | vector | 44.44% | 0.2815 |
| metadata | hybrid | 44.44% | 0.3333 |
| metric | bm25 | 33.33% | 0.1806 |
| metric | vector | 44.44% | 0.2685 |
| metric | hybrid | 33.33% | 0.2917 |

## 未命中示例（hybrid answer-level，前 10 条）

- `q021` WFCG 发表于哪一年？（gold p.1）
- `q022` WFCG 的发表期刊/会议是什么？（gold p.1）
- `q023` WFCG 的主方法名称是什么？（gold p.1）
- `q024` WFCG 在 Indian Pines 上使用多少训练比例和 patch size？（gold p.7）
- `q025` WFCG 在 Indian Pines、1% 训练比例下的 OA 是多少？（gold p.9）
- `q026` WFCG 在 Indian Pines、1% 训练比例下的 AA 是多少？（gold p.9）
- `q027` WFCG 在 Indian Pines、1% 训练比例下的 Kappa 是多少？（gold p.9）
- `q028` WFCG 在 University of Pavia、0.1% 训练比例下的 OA 是多少？（gold p.9）
- `q029` WFCG 在 University of Pavia、0.1% 训练比例下的 AA 是多少？（gold p.9）
- `q030` WFCG 在 University of Pavia、0.1% 训练比例下的 Kappa 是多少？（gold p.9）

