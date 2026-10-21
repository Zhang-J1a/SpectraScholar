# 真实论文评测集（3 篇已评测）

本目录用于存放**合法获取**的论文、人工标注与评测结果。PDF 保存在本地
`workspace/papers/`（已被 Git 忽略），**不随仓库分发**。

当前工作区已有：

- HybridSN：DOI 10.1109/LGRS.2019.2918719
- SSRN：DOI 10.1109/TGRS.2017.2755542
- WFCG：IEEE TIP 2022，Weighted Feature Fusion of CNN and GAT
- 2 份中文精读笔记（HyperAE、F2HNN）：只作为“非论文输入”的鲁棒性对照，**不计入准确率分母**

标注文件：`real_papers.labels.json`。标注只记录能在原文表格/正文确认的字段；无法确认的写
`null`。共 24 条指标、8 个实验条件、9 个数据集字段。

## 运行

```bash
python scripts/evaluate_real_papers.py
```

脚本会分别运行 heuristic 和 LLM（DeepSeek）抽取，输出：

- `docs/real_paper_runs.json`
- `docs/real_paper_runs.md`

## 当前结果（3 篇小样本）

| 指标 | heuristic | LLM |
|---|---|---|
| title | 0/3 | 3/3 |
| year | 3/3 | 3/3 |
| venue | 2/3 | 3/3 |
| 主方法 | 2/3 | 3/3 |
| 数据集 | 8/9 | 9/9 |
| 实验条件 | 0/8 | 4/8 |
| 指标数值 | 12/24 | 18/24 |
| 指标→数据集绑定 | 12/24 | 17/24 |
| 指标→比例/patch 绑定 | 0/24 | 6/24 |

**关键限制**：指标→数据集绑定仅 17/24（文本表 + Tesseract OCR），OCR 仍有误读/列错位；不能据此做真实论文的跨论文排名；这属于抽取子问题，
不是“论文结论已被验证”。不要复用合成夹具的数字作为真实结论。

## 候选论文清单

见 `papers.manifest.json`；GCN-HSI 仍未下载。PDF 的下载和使用请遵守出版商条款与所在机构许可。
