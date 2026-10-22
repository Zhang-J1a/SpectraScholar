# 真实论文检索评测

- 生成时间：2026-10-22T05:28:12+00:00
- 问题数：30
- chunk 数：250
- Answer hit：同一文档，且 gold page 或 gold answer 出现在 chunk；比只命中 gold page 宽。
- Page hit：必须命中人工标注的 gold page；更严格。
- `hash` 是词法哈希，不是语义 embedding。

## Answer-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 6.67% | 30.00% | 33.33% | 0.1694 |
| hash | 23.33% | 26.67% | 40.00% | 0.2783 |
| hybrid | 20.00% | 30.00% | 36.67% | 0.2539 |

## 严格 Page-level 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 0.00% | 26.67% | 30.00% | 0.1083 |
| hash | 10.00% | 10.00% | 23.33% | 0.1283 |
| hybrid | 13.33% | 20.00% | 26.67% | 0.1689 |

## 分类（answer-level）

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 0.00% | 0.0000 |
| condition | hash | 0.00% | 0.0000 |
| condition | hybrid | 0.00% | 0.0000 |
| metadata | bm25 | 44.44% | 0.2963 |
| metadata | hash | 66.67% | 0.5278 |
| metadata | hybrid | 55.56% | 0.4167 |
| metric | bm25 | 33.33% | 0.1343 |
| metric | hash | 33.33% | 0.2000 |
| metric | hybrid | 33.33% | 0.2148 |

## 未命中示例（hybrid answer-level，前 10 条）

- `q014` SSRN 在 Indian Pines 上使用多少训练比例和 patch size？（gold p.6）
- `q019` SSRN 在 University of Pavia、10% 训练比例下的 AA 是多少？（gold p.7）
- `q020` SSRN 在 University of Pavia、10% 训练比例下的 Kappa 是多少？（gold p.7）
- `q021` WFCG 发表于哪一年？（gold p.1）
- `q022` WFCG 的发表期刊/会议是什么？（gold p.1）
- `q023` WFCG 的主方法名称是什么？（gold p.1）
- `q024` WFCG 在 Indian Pines 上使用多少训练比例和 patch size？（gold p.7）
- `q025` WFCG 在 Indian Pines、1% 训练比例下的 OA 是多少？（gold p.9）
- `q026` WFCG 在 Indian Pines、1% 训练比例下的 AA 是多少？（gold p.9）
- `q027` WFCG 在 Indian Pines、1% 训练比例下的 Kappa 是多少？（gold p.9）

