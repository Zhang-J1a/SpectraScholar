# Tool Calling：arXiv 搜索

这是 V2.1 的工具层，不是 prompt 里“让模型假装搜索”。

## 端点

```http
GET /api/v1/tools/arxiv_search
```

参数：

| 参数 | 说明 |
|---|---|
| `query` | 必填，关键词或 arXiv 字段语法 |
| `year_from` / `year_to` | 年份区间，会转换成 `submittedDate` |
| `task_topic` | 任务主题过滤，拆词后追加 `all:` |
| `start` | 分页起点，默认 0 |
| `max_results` | 返回数，1–50 |
| `X-API-Key` | 如果设置了 `API_KEY` |

示例：

```powershell
$params = @{
  query = "hyperspectral graph neural network"
  year_from = 2020
  year_to = 2026
  task_topic = "hyperspectral classification"
  max_results = 3
}
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/tools/arxiv_search" -Body $params
```

返回包含：

- `papers[]`：`arxiv_id/title/authors/year/doi/abstract/pdf_url/categories/task_topic_match`
- `effective_query`：实际发送给 arXiv 的查询
- `duplicates_filtered`：DOI/arXiv ID 去重数
- `has_more`、`attempts`、`provider`

## 实现细节

- 普通关键词会转成 `all:term AND ...`，避免 arXiv 把裸查询当成宽泛相关搜索；
- 年份转成 `submittedDate:[YYYYMM010000 TO YYYYMMDD2359]`；
- `task_topic` 拆词后追加 `all:`，避免整句精确匹配导致 0 结果；
- 按 DOI 去重；没有 DOI 时用 arXiv ID，最后用标题；
- `arxiv.Client` 自带重试，外层再包一层有限重试；
- API 用 `asyncio.to_thread` + 硬超时，避免阻塞事件循环；
- 离线测试注入假客户端，不访问网络。

## 接入工作流

创建 workflow 时显式请求工具：

```json
{
  "topic": "hyperspectral graph neural network",
  "document_ids": ["<doc-1>", "<doc-2>"],
  "tools": ["arxiv_search"],
  "arxiv_year_from": 2020,
  "arxiv_year_to": 2026,
  "arxiv_max_results": 5
}
```

`plan` 节点会调用工具，记录：

- `tool_calls[]`：参数、状态、返回数、错误；
- `arxiv_results[]`：标题/年份/DOI/URL；
- 报告中的“外部工具调用（arXiv）”小节。

边界：

- 工具结果**不进入** `PaperExtraction` 的本地证据链；
- 不参与可比组/排名；
- 工具失败/超时只写提示，不伪造结果，也不阻塞本地 PDF 流程；
- 当前选择是请求方显式指定，不是 LLM 自主决定。

## 自主 Tool Calling 循环（V2.2）

另有 `POST /api/v1/tools/agent_loop`：

- LLM planner 在 `arxiv_search` / `local_search` 中选择；
- 最多 5 步，失败不无限重试；
- 每步记录 observation；
- 到上限强制收尾。

真实 DeepSeek planner 已用 `local_search` 跑通；详见 [`AGENT_LOOP.md`](AGENT_LOOP.md)。  
当前仍不是无限自主 Agent，也没有长期记忆。

## 真实调用记录

2026-10-21 真实调用：

```text
query: hyperspectral graph neural network
year: 2020–2026
task_topic: hyperspectral classification
max_results: 3
returned: 3
attempts: 1
duplicates_filtered: 0
```

返回示例（标题截断）：

```text
2609.39871 2026 A PyTorch Library for Hyperspectral Image Models: Technical Report
2411.07608 2024 Quantum Information-Empowered Graph Neural Network for Hyperspectral Change Detection
2502.16289 2025 MOB-GCN: A Novel Multiscale Object-Based Graph Neural Network for Hyperspectral Image Classification
```

## 工作流接入验证

2026-10-22 用两篇本地 PDF + `tools=["arxiv_search"]` 真实运行：

```text
workflow status: completed
tool_calls: arxiv_search status=failed error=timeout
report: 包含“外部工具调用（arXiv）”，工具失败未阻塞本地流程
```

这说明失败路径和证据隔离生效；成功路径由离线假客户端测试覆盖。  
真实网络恢复后应再跑一次完整成功路径，不能把本次超时写成“工具成功”。

## 限制

- 该工具已接入 7 节点工作流的 `plan` 节点：`WorkflowRequest.tools=["arxiv_search"]` 时调用；
- 这是**显式工具选择**，不是 LLM 在运行时自主决定；`tools` 为空时完全保留原本地 PDF 流程；
- 工具失败/超时会记入 `tool_calls` 和报告提示，但不会伪造文献，也不会让本地工作流失败；
- arXiv 的排序/字段语法会变化，`effective_query` 必须保留以便复盘；
- 结果相关性仍要人工判断，`task_topic_match` 只是词面匹配，不是语义相关性；
- 真实网络不可达时返回 503/504，不伪造空结果为成功。
