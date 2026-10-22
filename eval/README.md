# 评测数据

本目录保存评测标注与示例，不包含论文 PDF。  
PDF 需要自行合法获取并放入 `workspace/papers/`（该目录不随仓库分发）。

## 文件

| 文件 | 用途 |
|---|---|
| `real_papers.labels.json` | 3 篇真实论文的字段标注 |
| `research_eval.json` | 50 道检索题，含 `document_id/page/answer/quote` |
| `papers.manifest.json` | 论文元数据清单 |
| `extraction_labels.example.json` | 抽取标注模板 |
| `rag_queries.example.json` | RAG 查询示例 |

## 检索评测

```bash
python scripts/evaluate_retrieval.py --ocr --embedding hash
python scripts/evaluate_retrieval.py --ocr --embedding ollama
```

输出：

```text
docs/retrieval_runs.md
docs/retrieval_runs.json
```

50 题结果与限制见 [docs/EVALUATION.md](../docs/EVALUATION.md) 和
[docs/EMBEDDING_EVAL.md](../docs/EMBEDDING_EVAL.md)。

## 抽取评测

```bash
python scripts/evaluate_real_papers.py
```

脚本需要本地 PDF；输出目录可通过参数或环境配置调整。
