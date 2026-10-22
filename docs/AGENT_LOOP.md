# 自主 Tool Calling 循环（V2.2）

## 端点

```http
POST /api/v1/tools/agent_loop
```

请求：

```json
{
  "query": "What methods are discussed in the local papers?",
  "max_steps": 3,
  "allowed_tools": ["arxiv_search", "local_search"]
}
```

响应：

```json
{
  "query": "...",
  "answer": "...",
  "stopped_reason": "planner_finish",
  "steps": 2,
  "observations": [
    {"step": 1, "tool": "local_search", "status": "completed", "result": {}}
  ],
  "sources": []
}
```

## 设计

- **有界**：默认 3 步，最大 5 步；
- LLM 每步只返回一个 JSON：
  - `tool_call`：选择 `arxiv_search` 或 `local_search`；
  - `finish`：给出最终答案；
- 工具失败/超时会记录为 observation，不会无限重试；
- 到达上限时强制收尾，不会继续调用工具；
- 只允许白名单工具；
- 外部检索/本地检索的结果都保留 source 记录；
- 不把 arXiv/网页结果写成“本地 PDF 逐字证据”。

## 真实运行

2026-10-22，用真实 DeepSeek planner、只允许 `local_search`：

```text
query: What methods are discussed in the local papers?
max_steps: 1
stopped_reason: max_steps
observations: [('local_search', 'completed', None)]
answer: 基于本地论文的 HyperAE / 超图方法摘要
```

说明：

- planner 真实调用了 DeepSeek；
- 工具真实调用了本地 RAG；
- 因为 `max_steps=1`，最终由强制收尾生成答案，而不是 planner 主动 finish；
- 这证明不是纯 mock。

## 离线测试

`tests/test_agent_loop.py` 覆盖：

- 先调用工具再 finish；
- 非法工具被拒绝；
- 最大步数截断；
- API 端点返回 observation。

## 边界

- 不是无限自主 Agent；
- 没有长期记忆；
- 没有 human-in-the-loop；
- 没有真实网页搜索工具（网页研究仍由 GPTR 负责）；
- 不是 LangGraph；当前是自建有界状态循环。
