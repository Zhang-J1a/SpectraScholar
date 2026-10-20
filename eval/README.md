# 真实论文评测集（尚未下载）

本目录用于存放**合法获取**的论文、人工标注与评测结果。当前开发环境的外网被阻断
（arXiv / IEEE / PyPI 直连失败），因此本仓库**没有**真实论文 PDF，也**没有**真实论文上的
抽取或检索指标。不要把这些目录中的占位内容当成实验结果。

## 建议流程

1. 通过学校/机构订阅或开放获取渠道下载 PDF，保存到你自己的 `workspace/papers/`
   或本目录的 `pdfs/`（`pdfs/` 已被 Git 忽略）。
2. 按 `extraction_labels.example.json` 标注标题、方法、数据集、指标、训练比例、页码和
   原文片段。**只标注你能在原文确认的内容**；找不到就写 `null`。
3. 按 `rag_queries.example.json` 编写问题、相关文档和页码。
4. 运行：

```bash
python scripts/evaluate_pipeline.py      # 合成夹具，验证流水线
python scripts/evaluate_evidence.py comparison.json
```

真实论文评测需要在具备网络的环境中补充脚本参数；不要复用合成夹具的数字作为真实结论。

## 候选论文清单

见 `papers.manifest.json`。清单只记录公开元数据，PDF 未随仓库分发。下载和使用请遵守
出版商条款与所在机构许可。
