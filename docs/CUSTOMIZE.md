# 二次开发导航：从哪个文件开始？

## 先改这五处

1. `spectrascholar/domains.py`：领域名称、分析要求、报告结构提示。换成医疗/金融/法律文档也可，但请重新评测。
2. `spectrascholar/extraction/heuristic.py`：数据集、模型、图构建、指标关键词与规则。
3. `spectrascholar/schemas.py`：论文实体、证据、对比、RAG、工作流的数据契约；先改契约，再改实现。
4. `spectrascholar/compare.py`：可比性规则、指标表、单篇画像、Markdown 报告。
5. `web/index.html`：界面。前端是展示层，不能替代后端证据能力。

## 进阶修改

| 想做什么 | 改哪里 |
|---|---|
| 增加 LLM 抽取字段 | `extraction/llm.py` 的 Prompt + `build_paper_from_draft` |
| 扩展表格解析 | 改 `extraction/tables.py`，输出同样的 `MetricRecord(source="table")`，不要绕过证据层 |
| 增加 OCR | `evidence.read_pdf_pages` 前置 fallback；保持页码映射 |
| 换真实向量库 | `rag/index.py` 的 `add_document/search/remove_document` |
| 换 reranker | `rag/index.py` 的 `rerank` 分支；保留分数可解释性 |
| 换任务队列 | `api/research.py` 的 `tasks.add_task` → RQ/Celery；状态仍写 `store.py` |
| 多用户 | `documents/jobs/comparisons/workflows` 加 owner 字段；所有查询过滤；鉴权 |
| 换 PostgreSQL | 把 `store.py` 抽成 repository；SQL 迁移；保留接口 |
| 用 LangGraph | 把 `workflow.STEP_FUNCTIONS` 包装成节点；保留 `WorkflowState` 和 `workflow_steps` |
| 换前端 | 保留 API 契约；不要在前端做证据判断 |

## 推荐个人创新方向

- **HSI SOTA Comparison**：模型-数据集-样本比例-补丁-训练次数-指标组合；条件不同不排名。
- **Graph Construction Inspector**：KNN/RBF/静态/动态图、节点粒度、更新频率。
- **Evidence First RAG**：页码 + 最短原文片段 + 实验上下文三重契约。
- **Failure-aware Research**：429、超时、PDF 无文本、DB 损坏的可靠降级。

## 不要做

- 仅改项目名/Prompt/Logo 就宣称完成；
- 把 GPT Researcher 的搜索/报告写成个人原创；
- 用演示数据或合成夹具冒充真实论文指标；
- 一次引入 Milvus/FAISS/Chroma/pgvector 四套系统；
- 在没有真实评测前写“准确率提升 X%”。

每做一项功能：至少一个自动测试、一个 bad case、一段设计决策说明。
