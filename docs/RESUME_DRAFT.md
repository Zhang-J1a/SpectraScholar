# 简历项目描述（只使用已验证事实）

> 当前可用的真实数字：102 tests / 85% coverage / 合成夹具 20/20 字段、23/23 证据、4/4 引用、7/7 工作流；真实 GPT Researcher 本地 PDF 模式 + DeepSeek 完成 10/10 任务（报告均值 14.7k 字符，p50 24.0s / p95 33.5s，上游估算 $0.663）；Tavily 网页任务完成 10/10（均值 20.2k 字符、62 个来源、p50 36.9s，当前代理环境需临时放行）；3 篇真实论文抽取中 LLM 元数据/方法/数据集 3/3、9/9、指标数值 21/24，文本表 + Tesseract OCR 后指标→数据集 21/24；BM25/向量/混合在 hash 下并列 1.0，不能宣称语义提升。Docker 本机 build/up/worker 已验证；第二台机器和浏览器截图未验证。

**SpectraScholar — 科研文献调研与分析 Agent（个人二次开发）**

基于 GPT Researcher（Apache-2.0）进行业务扩展，构建可追溯、可比较、可测试的科研文献 Agent：FastAPI 后端、中文 Web UI、PDF 管理、结构化抽取、多论文可比性分析、混合 RAG 与引用核验。

技术栈：Python 3.12、FastAPI、Pydantic、SQLite、BM25、GPT Researcher、Docker（本机 build/up 验证）。

个人工作：

- 设计 `ResearchBackend` 适配层与任务状态机，加入 Trace ID、执行事件、超时、有限重试与可重试/不可重试错误分类；Demo 模式在 API/报告/页面显式标注，不冒充真实研究。
- 为 GPT Researcher 设计每任务隔离配置，正确处理 web/local、DOC_PATH、模型与检索器；用假引擎覆盖失败路径，并完成 10 次 DeepSeek 本地 PDF 真实任务（10/10，p50 24.0s）和 10 次 Tavily 网页任务（10/10，均值 20.2k 字符、62 个来源）。
- 抽象 OpenAI/DeepSeek 兼容聊天凭据与 provider 密钥检查；新增 SQLite 持久队列与独立 worker，跨进程恢复 queued 任务；增加 queued/running 取消、时间/成本预算和条件写入，防止 late worker 覆盖取消状态；
- 实现 arXiv Tool Calling：关键词转 `all:` 查询、年份/主题过滤、DOI 去重、分页、重试和硬超时；真实调用返回 3 篇相关论文，并保留 `effective_query` 便于复盘。DeepSeek-only 时自动切换 `deepseek-chat` 并设置 `CONTEXT_FILTER=keyword`，避免隐式调用不存在的 embedding 服务。
- 通过 `WorkflowRequest.tools=["arxiv_search"]` 接入 7 节点工作流的 `plan` 节点；工具结果写入独立 `tool_calls`/报告，不进入本地 PDF 证据链，失败不阻塞本地流程。
- 实现有界自主 Tool Loop：DeepSeek planner 在 `arxiv_search`/`local_search` 间选择，最多 5 步，记录 observation；真实 planner + local_search 跑通，非法工具/步数上限有测试。
- 设计 Pydantic 证据契约，将方法/模型家族/数据集/OA/AA/Kappa/训练比例/图构建绑定到 PDF 页码与连续原文片段；LLM 候选不匹配即拒绝，缺失字段返回 null。
- 建立 3 篇真实论文（HybridSN/SSRN/WFCG）人工标注与评测：LLM 元数据/方法/数据集 3/3、9/9、指标数值 21/24；文本表 + Tesseract OCR 把指标→数据集从 0/24 提升到 21/24，OCR 仍可能误读。
- 建立 30 题真实论文检索基线（Answer-level Recall@5 BM25/Ollama-vector/hybrid/题型路由 36.7%/43.3%/36.7%/50.0%，严格 page-level 33.3%/30.0%/23.3%/33.3%；路由仅比 hash 46.7% 高 3.3 点），并实现 claim-level 引用映射；不把基线结果写成语义提升。
- 使用 pdfplumber 解析带线 OA/AA/Kappa 表格，把行识别为方法、列识别为指标；数值仍回页文本核验，多值单元格拒绝；表格指标与正文指标去重合并。
- 实现多论文可比性分析：以数据集、指标、训练比例、补丁尺寸、协议为分组键，条件不全不排名；输出带证据附录的 Markdown。
- 实现页级混合 RAG（BM25 + 向量 + RRF + 词法重排），空/低分拒答，回答带页级引用并复用引用审计；无有效引用的 LLM 回答自动降级为抽取式。
- 建立 102 个 pytest（覆盖率 85%），覆盖非法 PDF、缺 Key、超时重试、幻觉引用、不可比条件、空知识库、表格多值单元格、队列认领等失败路径；提供三份合成夹具评测、BM25/向量/混合消融脚本与真实论文评测模板。
- 使用真实 Uvicorn + HTTP 完成上传→研究→对比→索引→问答→工作流→下载的端到端冒烟。

需要后续补齐（不要提前写进简历）：

- 真实 GPT Researcher 10 个任务成功率/耗时/成本；
- 真实论文（HybridSN/SSRN/GCN-HSI）字段 F1、引用有效率、Recall@K；
- 真实 embedding vs hash 的 ablation（当前 hash 下三模式并列 1.0，不能写提升）；
- Docker 跨环境部署记录；
- 真实界面截图/演示视频。

面试说明：通用搜索/抓取/报告能力来自 Apache-2.0 上游；本人负责领域业务层、证据与可比性、RAG、工作流、接口/UI/测试与部署配置。
