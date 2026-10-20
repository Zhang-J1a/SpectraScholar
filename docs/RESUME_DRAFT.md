# 简历项目描述（只使用已验证事实）

> 当前可用的真实数字：56 tests / 87% coverage / 合成夹具 14/14 字段、14/14 证据、Recall@1/3=1.0、3/3 引用、7/7 工作流。真实 API、真实论文、Docker、浏览器截图均未验证。不要把合成夹具数字写成真实论文效果。

**SpectraScholar — 科研文献调研与分析 Agent（个人二次开发）**

基于 GPT Researcher（Apache-2.0）进行业务扩展，构建可追溯、可比较、可测试的科研文献 Agent：FastAPI 后端、中文 Web UI、PDF 管理、结构化抽取、多论文可比性分析、混合 RAG 与引用核验。

技术栈：Python 3.12、FastAPI、Pydantic、SQLite、BM25、GPT Researcher、Docker（配置未构建验证）。

个人工作：

- 设计 `ResearchBackend` 适配层与任务状态机，加入 Trace ID、执行事件、超时、有限重试与可重试/不可重试错误分类；Demo 模式在 API/报告/页面显式标注，不冒充真实研究。
- 为 GPT Researcher 设计每任务隔离配置，正确处理 web/local、DOC_PATH、模型与检索器；用假引擎完成成功、空报告、缺 Key、超时重试的 Mock 集成测试（真实 API 未验证）。
- 设计 Pydantic 证据契约，将方法/模型家族/数据集/OA/AA/Kappa/训练比例/图构建绑定到 PDF 页码与连续原文片段；LLM 候选不匹配即拒绝，缺失字段返回 null。
- 实现多论文可比性分析：以数据集、指标、训练比例、补丁尺寸、协议为分组键，条件不全不排名；输出带证据附录的 Markdown。
- 实现页级混合 RAG（BM25 + 向量 + RRF + 词法重排），空/低分拒答，回答带页级引用并复用引用审计；无有效引用的 LLM 回答自动降级为抽取式。
- 建立 56 个 pytest（覆盖率 87%），覆盖非法 PDF、缺 Key、超时重试、幻觉引用、不可比条件、空知识库等失败路径；提供合成夹具评测脚本与真实论文评测模板。
- 使用真实 Uvicorn + HTTP 完成上传→研究→对比→索引→问答→工作流→下载的端到端冒烟。

需要后续补齐（不要提前写进简历）：

- 真实 GPT Researcher 10 个任务成功率/耗时/成本；
- 真实论文（HybridSN/SSRN/GCN-HSI）字段 F1、引用有效率、Recall@K；
- OpenAI embedding vs hash 的 ablation；
- Docker 跨环境部署记录；
- 真实界面截图/演示视频。

面试说明：通用搜索/抓取/报告能力来自 Apache-2.0 上游；本人负责领域业务层、证据与可比性、RAG、工作流、接口/UI/测试与部署配置。
