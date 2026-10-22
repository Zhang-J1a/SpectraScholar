# 真实论文检索评测

- 生成时间：2026-10-22T05:18:47+00:00
- 问题数：30
- chunk 数：212
- Gold：人工标注的 document/page；只评检索/页码命中，不评回答语义。
- `hash` 是词法哈希，不是语义 embedding。

## 总览

| 模式 | Recall@1 | Recall@3 | Recall@5 | MRR@5 |
|---|---:|---:|---:|---:|
| bm25 | 6.67% | 26.67% | 30.00% | 0.1583 |
| hash | 10.00% | 10.00% | 26.67% | 0.1350 |
| hybrid | 13.33% | 20.00% | 33.33% | 0.1967 |

## 分类

| 类别 | 模式 | Recall@5 | MRR@5 |
|---|---|---:|---:|
| condition | bm25 | 0.00% | 0.0000 |
| condition | hash | 0.00% | 0.0000 |
| condition | hybrid | 0.00% | 0.0000 |
| metadata | bm25 | 33.33% | 0.1111 |
| metadata | hash | 11.11% | 0.0278 |
| metadata | hybrid | 44.44% | 0.1833 |
| metric | bm25 | 33.33% | 0.2083 |
| metric | hash | 38.89% | 0.2111 |
| metric | hybrid | 33.33% | 0.2361 |

## 未命中示例（hybrid，前 10 条）

- `q014` SSRN 在 Indian Pines 上使用多少训练比例和 patch size？（gold p.6）
- `q019` SSRN 在 University of Pavia、10% 训练比例下的 AA 是多少？（gold p.7）
- `q021` WFCG 发表于哪一年？（gold p.1）
- `q022` WFCG 的发表期刊/会议是什么？（gold p.1）
- `q023` WFCG 的主方法名称是什么？（gold p.1）
- `q024` WFCG 在 Indian Pines 上使用多少训练比例和 patch size？（gold p.7）
- `q025` WFCG 在 Indian Pines、1% 训练比例下的 OA 是多少？（gold p.9）
- `q026` WFCG 在 Indian Pines、1% 训练比例下的 AA 是多少？（gold p.9）
- `q027` WFCG 在 Indian Pines、1% 训练比例下的 Kappa 是多少？（gold p.9）
- `q028` WFCG 在 University of Pavia、0.1% 训练比例下的 OA 是多少？（gold p.9）

