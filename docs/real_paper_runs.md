# 真实论文抽取评测

- 生成时间：2026-10-22T03:20:29+00:00
- 语料：3 篇英文原论文 + 2 份中文精读笔记（后者排除）
- 标注：24 条指标、8 个实验条件、9 个数据集字段

| 模式 | title | year | venue | method | datasets | conditions | metric value | dataset+metric | conditioned | evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| heuristic | 0/3 | 3/3 | 2/3 | 2/3 | 8/9 | 0/8 | 12/24 | 12/24 | 0/24 | 176/176 |
| llm | 3/3 | 3/3 | 3/3 | 3/3 | 9/9 | 5/8 | 21/24 | 21/24 | 9/24 | 271/277 |

## 关键解释

- `metric value`：只要求指标名和数值命中，不要求绑定数据集；
- `dataset+metric`：要求同一指标还绑定到正确数据集；
- `conditioned`：再要求训练比例/ patch size 一致；
- `evidence`：抽取器接受的逐字证据 /（接受 + 拒绝）；
- 这是抽取保真度评测，不代表论文结论正确性，也不代表跨论文可比性。

原始结果：[`real_paper_runs.json`](real_paper_runs.json)。
