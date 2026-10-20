# 可复制给 Codex 的任务（先做第一阶段）

你现在担任这个仓库的资深 Python AI Agent 工程师。请以 `README.md`、`docs/ROADMAP.md`、`docs/CUSTOMIZE.md` 为需求与边界，优先完成 **V1 真实科研 Agent 跑通**。

## 背景
- 项目已有 FastAPI、PDF 上传、SQLite 任务状态、GPT Researcher adapter、最小网页与论文比较基线。
- 用户是 AI/高光谱方向研究生，目标是 AI Agent / Python AI 后端实习。
- 不要从零重写 GPT Researcher，也不要复制整个上游库作为“原创”。

## 第一批任务（逐个完成，先列出计划）
1. 检查当前依赖是否兼容 Python 3.12。先运行 `pytest -q`，修复实际失败，禁止直接跳过失败测试。
2. 明确 `.env` 缺项并用可理解的报错说明。完成 GPT Researcher API 集成的 smoke test（没有真实 Key 时可编写隔离的假实现测试，不能假称联网成功）。
3. 确认本地 PDF 模式真实读取 `workspace/papers`，以及能生成带来源的真实研究报告；不能仅信任模型生成的来源。
4. 为 `/api/v1/research` 增加最大执行时长、任务日志以及失败重试策略；区分暂时性错误与不可重试错误。
5. 为 PDF 抽取建立基础真实测试集：HybridSN、SSRN、GNN 论文。返回页码、原文、数据集/模型名/实验条件；缺失信息为空，不允许编造。
6. 更新 README，只陈述自己运行和验证过的能力，不制造成功率/加速比例。

## 工程要求
- 新增代码保持 `spectrascholar/` 内模块化，优先依赖注入和小函数。
- 数据模型用 Pydantic，密钥只在 `.env`，禁止输出密钥。
- 不允许把真实用户论文或论文全文提交到 Git，遵守版权限制。
- 对外部 API 加限流、超时与失败退出，查询只读；上传文件做限制与路径隔离。
- 每个功能提供一组 pytest，用实际失败修复过程证明实现。
- 每次提交列出：修改文件、技术决策、运行命令、测试结果、未完成的问题。

## 禁止
- 仅修改系统 Prompt、项目 Logo 或 README 就宣布“Agent 项目完工”。
- 把 GPT Researcher 的 Planner、多 Agent、RAG 等上游实现写成个人原创。
- 虚构评测指标或真实论文实验精度。
- 一口气新增复杂多智能体、Kubernetes、MCP、消息队列而不完成基本调研闭环。
