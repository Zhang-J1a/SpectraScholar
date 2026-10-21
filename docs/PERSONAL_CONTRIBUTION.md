# 个人贡献说明

> 目的：在简历、GitHub 和面试中准确区分 **GPT Researcher 上游能力** 与 **本人新增实现**。
> 统计口径：`spectrascholar/` 下 Python 源文件共 5,965 行（含注释/空行，2026-10-21）；测试 1,463 行；脚本 1,244 行；Web 897 行。

## 1. 上游：GPT Researcher（Apache-2.0）

- 仓库：<https://github.com/assafelovic/gpt-researcher>
- 版本：`gpt-researcher==0.16.1`（本项目的 live extra）
- 使用方式：作为 Python 依赖，通过 `GPTResearcher` 公共 API 调用：
  - `conduct_research()`
  - `write_report()`
- 上游负责：
  - 网页搜索/检索器集成；
  - 网页抓取与上下文管理；
  - 报告生成；
  - 上游的多 Agent/规划流程；
  - 上游自己的配置系统。

**本项目没有把上述能力写成个人原创，也没有复制上游源码到 `spectrascholar/`。**

## 2. 本人新增/重构的模块

### 2.1 研究适配与任务系统

| 文件 | 工作 |
|---|---|
| `spectrascholar/research.py`（357 行） | `ResearchBackend` 协议、Demo/GPT Researcher 适配器、每任务配置、超时、有限重试、错误分类、任务事件、引用审计、报告头 |
| `spectrascholar/api/research.py` | 提交/列表/详情/事件/下载/重试、并发限制 |
| `spectrascholar/store.py`（566 行） | SQLite schema/迁移、短连接显式关闭、任务/事件/文档/对比/工作流 |
| `spectrascholar/settings.py` | 统一配置、模型/超时/RAG/工作流参数 |
| `spectrascholar/logging_utils.py` | Trace ID、JSON/文本日志 |
| `spectrascholar/llm_config.py` | OpenAI/DeepSeek 聊天凭据解析；OpenAI 优先 |

### 2.2 结构化抽取与证据

| 文件 | 工作 |
|---|---|
| `spectrascholar/schemas.py`（440 行） | Pydantic 契约：EvidenceRef、ExtractedField、PaperExtraction、Comparison、Citation、RAG、Workflow |
| `spectrascholar/evidence.py`（188 行） | PDF 页读取、页码/原文/值核验、状态判定 |
| `spectrascholar/extraction/heuristic.py`（483 行） | 规则抽取：元数据、模型家族、数据集、图构建、指标、训练比例、补丁、协议 |
| `spectrascholar/extraction/llm.py`（399 行） | LLM JSON 抽取、修复、逐字拒绝、rejection 记录 |
| `spectrascholar/extraction/tables.py`（411 行） | pdfplumber 表格检测、方法级 OA/AA/Kappa、条件上下文、证据拒绝、正文合并 |
| `spectrascholar/extraction/service.py` | 模式解析、表格合并、统一错误、证据计数 |
| `spectrascholar/citations.py`（239 行） | 本地引用解析、外部链接、缺引用数值结论、报告审计节 |

### 2.3 多论文对比

| 文件 | 工作 |
|---|---|
| `spectrascholar/compare.py`（463 行） | 方法行、数据集矩阵、指标行、可比组、单篇画像、Markdown 报告 |
| `spectrascholar/api/comparison.py` | 对比接口、持久化、Markdown 下载 |

**个人技术点**：把“训练比例/补丁/协议”作为可比性硬条件；条件缺失时拒绝排名，而不是只比较 OA 数字。

### 2.4 混合 RAG

| 文件 | 工作 |
|---|---|
| `spectrascholar/rag/chunking.py` | 页级 chunk，保留页码/偏移，不跨页 |
| `spectrascholar/rag/bm25.py` | 纯 Python BM25，中英文 token |
| `spectrascholar/rag/embeddings.py` | hash（离线词法）/ OpenAI embedding |
| `spectrascholar/rag/index.py`（295 行） | 内存向量 + BM25 + RRF + 词法重排 + JSON 持久化 |
| `spectrascholar/rag/service.py`（371 行） | 索引、检索、抽取式/LLM 回答、拒答、引用审计 |
| `spectrascholar/api/knowledge.py` | 索引/检索/问答/清空接口 |

### 2.5 工作流与工程化

| 文件 | 工作 |
|---|---|
| `spectrascholar/workflow.py`（354 行） | 7 节点 DAG、节点状态/重试/超时/失败持久化、报告 |
| `spectrascholar/api/workflows.py` | 提交/查询/下载/幂等 |
| `spectrascholar/main.py`（135 行） | App 工厂、路由、Trace、限流、安全头、统一错误 |
| `spectrascholar/api/documents.py`（141 行） | 上传安全、去重、页查看、删除联动索引 |
| `spectrascholar/api/system.py` | health、config、单条证据核验 |
| `web/index.html`（897 行） | 中文单页 UI、轮询、Markdown、引用跳转、工作流 |
| `tests/`（1,463 行） | 68 个测试、PDF/表格工厂、Mock GPT Researcher/LLM |
| `scripts/`（1,244 行） | 合成夹具评测、10 任务本地/网页真实研究评测、3 篇真实论文评测、BM25/向量/混合消融、GPT Researcher 检查/真实冒烟、证据统计 |
| `Dockerfile` / `compose.yaml` / `.env.example` | 部署与配置（Docker 构建未验证） |

## 3. 明确不属于本人的工作

- GPT Researcher 的搜索、抓取、上下文管理、报告生成、上游 Agent 流程；
- OpenAI/embedding 模型的训练；
- PyPDF/FastAPI/Pydantic/SQLite 等开源库；
- 真实论文作者的研究成果与实验数据。

## 4. 可验证的个人成果

- 68 个 pytest 通过，覆盖率 87%；
- `ruff` 全绿；
- 真实 Uvicorn HTTP 冒烟：上传→研究→对比→索引→问答→工作流→下载均成功；
- 合成夹具：字段 20/20、证据 23/23、引用 4/4、工作流 7/7；
- 表格夹具：6 条 `source=table` 方法级指标、1 个数据集、多值单元格拒绝；
- BM25/向量/混合消融均跑通；hash 词法嵌入下三模式并列 1.0，不宣称语义提升；
- 真实 DeepSeek：聊天、LLM 抽取（12/12 候选）、RAG 回答均完成；
- 真实 GPT Researcher 本地 PDF 模式：10/10 任务 completed，报告均值 14.7k 字符，p50 24.0s / p95 33.5s，上游估算 $0.663；
- 真实 Tavily 网页任务：10/10 completed，均值 20.2k 字符、p50 36.9s、62 个来源、上游估算 $1.078；
- 3 篇真实论文抽取：LLM 的 title/year/venue/方法 3/3、datasets 9/9、指标数值 13/24、条件 4/8；指标→数据集绑定 0/24；
- 明确记录的失败路径：缺 Key、超时、空报告、幻觉引用、不可比条件、空知识库、表格多值单元格、指标未绑定数据集。

## 5. 不能声称的成果

- 真实 GPT Researcher **网页引用正确或生产稳定**（10 次任务完成，但 443 条外部链接未核验，且代理环境需临时放行）；
- 真实论文**指标可直接排名**（指标→数据集绑定 0/24）；完整 token 成本未统计；
- Docker 部署验证通过（无 Docker CLI）；
- 浏览器视觉截图（被沙箱阻断）；
- 上游搜索/报告能力为本人原创。

## 6. 建议的 Git 提交叙事

```text
chore: import SpectraScholar starter baseline
feat: add resilient research job pipeline and GPT Researcher adapter
feat: add scientific paper extraction with page-level evidence
feat: add table-aware method-level metric extraction
feat: add multi-paper comparison and comparability checks
feat: add citation verification and report audit
feat: add hybrid BM25/vector RAG with grounded refusal
feat: add local literature workflow and engineering hardening
feat: rebuild the research workspace UI
test: cover failure paths, mock integrations and evaluation fixtures
docs: add architecture, evaluation, development log and interview guide
```

每次提交都对应实际文件改动；不把上游代码或演示数据伪装成个人成果。
