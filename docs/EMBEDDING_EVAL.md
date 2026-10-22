# 真实 Embedding / RAG 检索评测

## 入口

```powershell
# hash 基线（可离线）
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --ocr --embedding hash

# 任意 OpenAI-compatible embedding
$env:EMBEDDING_API_KEY="..."
$env:EMBEDDING_BASE_URL="https://api.siliconflow.cn/v1"
$env:EMBEDDING_MODEL="BAAI/bge-m3"
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --ocr --embedding openai
```

`EMBEDDING_API_KEY` 与聊天 Key 分离；不设置时才回退到 `OPENAI_API_KEY`。  
这样第三方 embedding 不会把 DeepSeek/OpenAI 聊天 provider 切走。

## 可选 provider

| Provider | Base URL | 示例模型 | 备注 |
|---|---|---|---|
| OpenAI | 空或 `https://api.openai.com/v1` | `text-embedding-3-small` | 官方 |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `BAAI/bge-m3` | OpenAI-compatible |
| Jina | `https://api.jina.ai/v1` | `jina-embeddings-v3` | 需确认账户/额度 |
| DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `text-embedding-v3` | 阿里云兼容模式 |
| Ollama | `http://localhost:11434/v1` | `nomic-embed-text` | Key 可填 `ollama`；本地 |
| LM Studio | `http://localhost:1234/v1` | 本地模型 | Key 任意占位 |
| vLLM / llama.cpp | 自定义 `/v1` | 本地 embedding 模型 | OpenAI-compatible |

不直接兼容 OpenAI 协议的 provider（例如部分 Azure OpenAI、Cohere、Voyage）需要单独 adapter，当前未接入。

本地 4 GB 机器优先考虑：

```text
Ollama nomic-embed-text
或 fastembed / ONNX 小模型
```

不建议在 4 GB 上跑 `bge-m3` + 完整 GPTR 同时运行。

## 当前状态

本机 `.env` **没有 `EMBEDDING_API_KEY`，也没有 `OPENAI_API_KEY`**，所以真实 embedding 没有运行：

```text
REAL_EMBEDDING_BLOCKED: missing_api_key
```

这不是代码失败，而是没有真实 embedding 凭据。  
DeepSeek 只提供 chat，不提供 embedding，不能用它代替。  
但可以用任何 OpenAI-compatible embedding 服务，或本地 Ollama/fastembed。

## 当前真实结果（hash）

```text
Answer-level Recall@5:
BM25 36.7%
hash 46.7%
hybrid 40.0%

严格 page-level Recall@5:
BM25 33.3%
hash 30.0%
hybrid 30.0%
```

hash 是词法哈希，不是语义模型；这些数字只能证明检索流水线，不证明语义能力。

## 有 Key 后要补的记录

- embedding 模型名；
- 维度、批量大小；
- 构建耗时、查询耗时；
- 与 hash 的同题对比；
- 是否真的提升 page-level/answer-level；
- 失败样本。

不要把“hash 46.7%”写成“语义检索提升”。
