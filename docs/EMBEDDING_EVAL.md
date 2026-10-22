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
| Ollama（原生） | `http://127.0.0.1:11434` | `nomic-embed-text` | `EMBEDDING_BACKEND=ollama`，无需 Key |
| Ollama（兼容层） | `http://localhost:11434/v1` | `nomic-embed-text` | `EMBEDDING_BACKEND=openai`，Key 填 `ollama` |
| LM Studio | `http://localhost:1234/v1` | 本地模型 | Key 任意占位 |
| vLLM / llama.cpp | 自定义 `/v1` | 本地 embedding 模型 | OpenAI-compatible |

不直接兼容 OpenAI 协议的 provider（例如部分 Azure OpenAI、Cohere、Voyage）需要单独 adapter，当前未接入。

本地 4 GB 机器优先考虑：

```text
Ollama nomic-embed-text
或 fastembed / ONNX 小模型
```

不建议在 4 GB 上跑 `bge-m3` + 完整 GPTR 同时运行。

## Ollama 安装与配置

当前机器**未安装 Ollama**（`ollama`、11434 端口均不存在）。

1. 下载 Windows 安装包：
   <https://ollama.com/download>
2. 安装到 `D:\Ollama`（如果安装器支持 `/DIR=D:\Ollama`；否则默认 C 盘）。
3. 模型目录放 D 盘（管理员 PowerShell，设置后重开终端）：

```powershell
setx OLLAMA_MODELS "D:\OllamaModels"
```

4. 启动：

```powershell
ollama serve
```

5. 拉取轻量 embedding 模型：

```powershell
ollama pull nomic-embed-text
```

6. `.env`：

```dotenv
EMBEDDING_BACKEND=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_TIMEOUT_SECONDS=120
```

7. 验证：

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --ocr --embedding ollama
```

注意：

- `nomic-embed-text` 约 274 MB，4 GB 内存可尝试；不要同时跑完整 GPTR + OCR；
- 原生 backend 调用 `/api/embeddings`，不依赖 Ollama 的 `/v1` 兼容层；
- 没有 Ollama 时返回 `ollama_unavailable`，不会回退成 hash 冒充真实 embedding。

## 当前状态

本机没有 `EMBEDDING_API_KEY`/`OPENAI_API_KEY`，也**未安装 Ollama**，所以真实 embedding 没有运行：

```text
--embedding openai → REAL_EMBEDDING_BLOCKED: missing_api_key
--embedding ollama → REAL_EMBEDDING_BLOCKED: ollama_unavailable
```

这不是代码失败，而是没有真实 embedding 凭据。  
DeepSeek 只提供 chat，不提供 embedding，不能用它代替。  
但可以用任何 OpenAI-compatible embedding 服务，或本地 Ollama/fastembed。

## 当前真实结果（Ollama nomic-embed-text，768 维）

```text
Answer-level Recall@5:
BM25          68.0%
hash          60.0%
Ollama vector 70.0%
hybrid        72.0%
router        76.0%

严格 page-level Recall@5:
BM25          62.0%
hash          52.0%
Ollama vector 64.0%
hybrid        70.0%
router        72.0%
```

路由：metadata → hash，metric/condition → Ollama vector，其余 hybrid。  
结论：**50 题扩样后，路由 Answer-level 76.0%，比 hash 60.0% 高 16 点；page-level 72.0%**；仍不能宣称语义检索已解决。  
当前评测 50 题、3 篇论文；仍需更大评测集和更强的多语言模型。

## 有 Ollama/Key 后要补的记录

- embedding 模型名；
- 维度、批量大小；
- 构建耗时、查询耗时；
- 与 hash 的同题对比；
- 是否真的提升 page-level/answer-level；
- 失败样本。

不要把“router 76.0%”写成“语义检索已解决”。
