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

## 限制

- 该工具目前是 **可调用端点**，还没有接入 7 节点工作流的“规划”节点做自主工具选择；
- arXiv 的排序/字段语法会变化，`effective_query` 必须保留以便复盘；
- 结果相关性仍要人工判断，`task_topic_match` 只是词面匹配，不是语义相关性；
- 真实网络不可达时返回 503/504，不伪造空结果为成功。
