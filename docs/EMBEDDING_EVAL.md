# Embedding 与检索评测

## 支持的 Backend

| Backend | 配置 | 说明 |
|---|---|---|
| `hash` | `EMBEDDING_BACKEND=hash` | 词法哈希；离线可跑，不是语义模型 |
| `openai` | `EMBEDDING_BACKEND=openai` | 任意 OpenAI-compatible `/v1/embeddings` |
| `ollama` | `EMBEDDING_BACKEND=ollama` | Ollama 原生 `/api/embeddings` |

### OpenAI-compatible

```dotenv
EMBEDDING_BACKEND=openai
EMBEDDING_API_KEY=...
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=BAAI/bge-m3
```

`EMBEDDING_API_KEY` 与聊天 Key 分离；不设置时才回退到 `OPENAI_API_KEY`。  
支持 SiliconFlow、Jina、DashScope、LM Studio、vLLM 等兼容 `/v1/embeddings` 的服务。

### Ollama

```bash
ollama pull bge-m3
ollama serve
```

```dotenv
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_TIMEOUT_SECONDS=120
```

小机器可先用 `nomic-embed-text`（768 维，约 274 MB）；`bge-m3` 为 1024 维、约 1.2 GB。

如果模型放在独立目录：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_ollama.ps1 `
  -OllamaExe "C:\path\to\ollama.exe" `
  -ModelsDir "D:\path\to\ollama_models"
```

该脚本只启动项目使用的独立 Ollama 进程，不修改系统服务。

---

## 50 题结果

数据：3 篇真实论文、50 道人工标注题；只评检索/page 命中。

### Answer-level Recall@5

| 模式 | R@1 | R@3 | R@5 | MRR@5 |
|---|---:|---:|---:|---:|
| BM25 | 32.0% | 58.0% | 68.0% | 0.465 |
| hash | 34.0% | 54.0% | 60.0% | 0.433 |
| bge-m3 vector | 54.0% | 70.0% | 78.0% | 0.630 |
| **bge-m3 hybrid** | 50.0% | 74.0% | **80.0%** | 0.611 |
| router | 44.0% | 62.0% | 70.0% | 0.540 |

### 严格 Page-level Recall@5

| 模式 | R@5 | MRR@5 |
|---|---:|---:|
| BM25 | 62.0% | 0.391 |
| hash | 52.0% | 0.354 |
| bge-m3 vector | 72.0% | 0.555 |
| **bge-m3 hybrid** | **72.0%** | 0.539 |
| router | 62.0% | 0.445 |

### nomic 对照

同一 50 题：

```text
Answer-level: vector 70.0% / hybrid 72.0% / router 78.0%
Page-level:   vector 64.0% / hybrid 70.0% / router 76.0%
```

结论：

- `bge-m3 + hybrid` 的 answer-level 最高（80.0%），page-level 72.0%；
- nomic 的 router 在 page-level 更高（76.0%），但 answer-level 较低；
- `router` 依赖 metadata→BM25 规则，换 embedding 后不一定最优；bge-m3 推荐显式使用 `hybrid`；
- 50 题、3 篇论文仍是小样本，不能外推为通用语义检索结论。

---

## 复现

```bash
# hash
python scripts/evaluate_retrieval.py --ocr --embedding hash

# Ollama (bge-m3)
python scripts/evaluate_retrieval.py --ocr --embedding ollama
```

输出：

```text
docs/retrieval_runs.md
docs/retrieval_runs.json
```

题目与 gold：

```text
eval/research_eval.json
```

论文 PDF 不随仓库分发，需要自行合法获取并放入 `workspace/papers/`。
