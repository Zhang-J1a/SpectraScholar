# 真实 Embedding / RAG 检索评测

## 入口

```powershell
# hash 基线（可离线）
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --ocr --embedding hash

# 真实 OpenAI embedding
$env:OPENAI_API_KEY="..."
.\.venv\Scripts\python.exe scripts\evaluate_retrieval.py --ocr --embedding openai
```

## 当前状态

本机 `.env` **没有 `OPENAI_API_KEY`**，所以真实 embedding 没有运行：

```text
REAL_EMBEDDING_BLOCKED: missing_api_key
```

这不是代码失败，而是没有真实 embedding 凭据。  
DeepSeek 只提供 chat，不提供 embedding，不能用它代替。

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
