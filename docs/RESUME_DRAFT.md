# 简历项目描述（只使用已验证事实）

> 当前可用的真实数字：68 tests / 87% coverage / 合成夹具 20/20 字段、23/23 证据、4/4 引用、7/7 工作流；真实 GPT Researcher 本地 PDF 模式 + DeepSeek 完成 2 次 API 任务（约 15k 字符报告）；BM25/向量/混合在 hash 下并列 1.0，不能宣称语义提升。真实网页检索、真实论文、Docker、浏览器截图未验证。

**SpectraScholar — 科研文献调研与分析 Agent（个人二次开发）**

基于 GPT Researcher（Apache-2.0）进行业务扩展，构建可追溯、可比较、可测试的科研文献 Agent：FastAPI 后端、中文 Web UI、PDF 管理、结构化抽取、多论文可比性分析、混合 RAG 与引用核验。

技术栈：Python 3.12、FastAPI、Pydantic、SQLite、BM25、GPT Researcher、Docker（配置未构建验证）。

个人工作：

- 设计 `ResearchBackend` 适配层与任务状态机，加入 Trace ID、执行事件、超时、有限重试与可重试/不可重试错误分类；Demo 模式在 API/报告/页面显式标注，不冒充真实研究。
- 为 GPT Researcher 设计每任务隔离配置，正确处理 web/local、DOC_PATH、模型与检索器；用假引擎覆盖失败路径，并完成 2 次 DeepSeek 本地 PDF 真实任务（网页检索未验证）。
- 抽象 OpenAI/DeepSeek 兼容聊天凭据与 provider 密钥检查；DeepSeek-only 时自动切换 `deepseek-chat` 并设置 `CONTEXT_FILTER=keyword`，避免隐式调用不存在的 embedding 服务。
- 设计 Pydantic 证据契约，将方法/模型家族/数据集/OA/AA/Kappa/训练比例/图构建绑定到 PDF 页码与连续原文片段；LLM 候选不匹配即拒绝，缺失字段返回 null。
- 使用 pdfplumber 解析带线 OA/AA/Kappa 表格，把行识别为方法、列识别为指标；数值仍回页文本核验，多值单元格拒绝；表格指标与正文指标去重合并。
- 实现多论文可比性分析：以数据集、指标、训练比例、补丁尺寸、协议为分组键，条件不全不排名；输出带证据附录的 Markdown。
- 实现页级混合 RAG（BM25 + 向量 + RRF + 词法重排），空/低分拒答，回答带页级引用并复用引用审计；无有效引用的 LLM 回答自动降级为抽取式。
- 建立 68 个 pytest（覆盖率 87%），覆盖非法 PDF、缺 Key、超时重试、幻觉引用、不可比条件、空知识库、表格多值单元格等失败路径；提供三份合成夹具评测、BM25/向量/混合消融脚本与真实论文评测模板。
- 使用真实 Uvicorn + HTTP 完成上传→研究→对比→索引→问答→工作流→下载的端到端冒烟。

需要后续补齐（不要提前写进简历）：

- 真实 GPT Researcher 10 个任务成功率/耗时/成本；
- 真实论文（HybridSN/SSRN/GCN-HSI）字段 F1、引用有效率、Recall@K；
- 真实 embedding vs hash 的 ablation（当前 hash 下三模式并列 1.0，不能写提升）；
- Docker 跨环境部署记录；
- 真实界面截图/演示视频。

面试说明：通用搜索/抓取/报告能力来自 Apache-2.0 上游；本人负责领域业务层、证据与可比性、RAG、工作流、接口/UI/测试与部署配置。
