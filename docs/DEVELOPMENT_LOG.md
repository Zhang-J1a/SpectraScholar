# SpectraScholar 开发日志

> 记录真实执行过程、遇到的 Bug、处理方案、测试结果与未完成事项。
> 环境：Windows 11，PowerShell 7，Python 3.12.8，日期 2026-10-20。
> 所有“通过”都对应本机实际命令；标为“未验证”的没有真实运行证据。

---

## 0. 初始工程审查（修改前）

### 已经真实存在的能力

- FastAPI 基础接口：研究任务提交、状态查询、报告下载、PDF 上传、文献列表、`/compare`。
- SQLite 任务与文档记录（`store.py`）。
- `DemoBackend`：明确标注演示，不调用搜索/LLM。
- `GPTResearcherBackend`：已有 `conduct_research()` / `write_report()` 调用骨架。
- PDF 读取（pypdf）、规则数据集匹配、页码 + 原文片段核验原语。
- 极简单页 Web UI。
- 5 个 pytest 离线测试。
- Dockerfile / compose / 环境变量模板。

### 仅有入口、未完成集成或未验证

| 项目 | 问题 |
|---|---|
| GPT Researcher 真实调用 | 未在真实 Key/网络下验证；本地模式配置不完整 |
| 任务状态可靠性 | 无执行日志、无尝试次数、无超时/重试分类、无 Trace |
| 结构化抽取 | 仅少量数据集字面匹配；没有方法/模型/实验条件/图构建 |
| 多论文对比 | 只有 JSON 拼接；没有可比性规则、不可比标记、Markdown 导出 |
| 引用核验 | 只有字段级函数；没有报告级审计、缺引用结论检测 |
| RAG | 未实现 |
| 工作流 | 未实现 |
| 测试 | 只覆盖 happy path；缺失败路径、Mock 集成、状态转换 |
| 工程化 | 无鉴权/限流/统一错误/Trace；`BackgroundTasks` 仅适合演示 |
| Docker | 未构建验证（本机无 Docker） |

### 审查时发现的具体 Bug / 风险

1. **本地模式配置错误**：只设置 `DOC_PATH`，没有让 GPT Researcher 的 `Config` 设置 `doc_path`。上游 `Config` 仅在 `REPORT_SOURCE != web` 时设置 `doc_path`；本地模式可能直接 `AttributeError`。
2. **SQLite 连接未关闭**：`with sqlite3.connect(...)` 只提交/回滚，不关闭连接。Windows 下导致测试工作区删除失败（WinError 32）。
3. **任务失败没有类型**：所有异常压成字符串，无法区分可重试与不可重试。
4. **列表接口返回完整报告**：任务多时响应过大。
5. **PDF 读取保持文件句柄**：pypdf 直接接收路径，可能延迟释放，影响 Windows 删除。
6. **测试隔离不足**：直接使用项目 `workspace`，会污染真实数据。
7. **旧测试只验证结果包含“演示模式”**，没有验证状态转换/日志/失败。

### 基线测试结果（修改前）

```powershell
cd SpectraScholar-Starter
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pytest -q
```

```text
.....                                                                    [100%]
5 passed, 2 warnings in 1.74s
```

> 说明：venv 的 `ensurepip` 在该环境失败，最终使用全局 `uv`（`python -m uv`）创建环境并安装依赖。

---

## 1. P0：真实调研链路与任务状态机

### 实现

- `research.py` 重写：
  - `ResearchOutcome` 明确 `backend/is_demo/metadata`；
  - `GPTResearcherBackend` 每任务写入隔离 JSON 配置，包含 `REPORT_SOURCE`、`DOC_PATH`、`LANGUAGE`、`RETRIEVER`、`FAST_LLM`/`SMART_LLM`/`STRATEGIC_LLM`；
  - 阶段超时 + 任务总超时；
  - `ResearchError(code, retryable)`；
  - 空上下文/空报告失败；
  - 缺 `OPENAI_API_KEY` / `TAVILY_API_KEY` / 依赖 → 明确错误；
  - Demo 与真实报告头显式区分。
- `store.py`：
  - `jobs` 增加 `language/backend/is_demo/error_type/citation_audit/trace_id/attempts/started_at/elapsed_ms`；
  - 新增 `job_events`；
  - `_ClosingConnection` 显式关闭连接；
  - 轻量迁移（`PRAGMA table_info` + `ALTER TABLE`）。
- `api/research.py`：提交、列表、详情、事件、下载、重试；并发上限。
- 引用审计：完成后自动生成 `CitationAudit` 并附到报告。

### 关键 Bug 与修复

#### Bug 1：本地模式配置不生效

**现象**：本地模式只设置 `DOC_PATH` 环境变量，但上游 `Config` 在 `REPORT_SOURCE=web` 时不读取 `DOC_PATH`，`cfg.doc_path` 可能不存在。

**修复**：为每次任务生成 `workspace/gptr_configs/<job_id>.json`：

```json
{
  "REPORT_SOURCE": "local",
  "DOC_PATH": ".../workspace/papers",
  "LANGUAGE": "chinese",
  "RETRIEVER": "tavily",
  "FAST_LLM": "openai:gpt-4o-mini",
  "SMART_LLM": "openai:gpt-4o",
  "STRATEGIC_LLM": "openai:gpt-4o"
}
```

把 `config_path` 传给 `GPTResearcher`。同时文档明确：不要再在 `.env` 设 `REPORT_SOURCE`，因为环境变量优先级高于配置文件。

**验证**：Mock 测试断言 `config_data["REPORT_SOURCE"] == "local"` 且 `DOC_PATH` 以 `papers` 结尾。

#### Bug 2：Windows 下 SQLite 文件锁

**现象**：pytest 第二个用例开始出现 `PermissionError: [WinError 32] ... sqlite3` / 工作区目录无法删除。

**原因**：`with sqlite3.connect(...)` 的上下文管理器只负责事务，不关闭连接；连接对象被 GC 前一直持有文件句柄。

**修复**：自定义 `_ClosingConnection(sqlite3.Connection)`，在 `__exit__` 中先 `super().__exit__` 再 `close()`，并作为 `factory` 传入 `sqlite3.connect`。

**验证**：当时 56 个测试连续运行，工作区每个用例可重建（后续扩展到 98 个）。

#### Bug 3：PDF 文件句柄影响删除

**修复**：`read_pdf_pages` / `pdf_page_count` 先 `path.read_bytes()`，再用 `BytesIO` 交给 pypdf；文件立即关闭。

#### Bug 4：任务列表返回完整报告

**修复**：新增 `JobSummary`；`recent_jobs` 只 SELECT 摘要字段；详情接口仍返回 `JobDetails`（含报告/审计）。

### Mock 集成测试覆盖

- 成功：`conduct_research()` / `write_report()` 被调用；`backend=gptr`、`is_demo=false`；
- 本地模式配置写入正确；
- 空报告 → `failed / empty_report`；
- 缺 Key → `failed / missing_api_key`；
- 超时 → 重试 2 次后 `failed / timeout`，存在 `retry` 事件；
- 失败任务可重试。

### 真实 API 状态

- 已阅读并核对 `gpt-researcher==0.16.1` 源码：
  - `GPTResearcher.__init__(query, report_type, report_source, report_format, config_path, ...)`
  - `async conduct_research()`
  - `async write_report()`
- **当时未完成真实联调**：环境无 API Key，且外网直连失败。后续用户提供 DeepSeek Key，已在 10.8 完成本地 PDF 真实任务。
- 尝试安装完整 live 依赖时，`sgmllib3k` sdist 构建在 Windows 沙箱内因临时目录 `chmod` 被拒绝而失败；后来通过手工补齐 `docopt/sgmllib3k/langdetect` 并安装剩余依赖完成 import，没有把失败包装成成功。
- 提供 `scripts/check_gptr_api.py` 与 `scripts/smoke_gptr.py`，在具备网络/Key 的环境可真实执行并明确输出失败。

---

## 2. P1-A：结构化抽取

### 实现

- `schemas.py` 新增：
  - `EvidenceRef`、`ExtractedField`、`PaperMetadata`、`MethodRecord`、`DatasetRecord`、`GraphConstructionRecord`、`ExperimentCondition`、`MetricRecord`、`ExtractionStats`、`RejectionRecord`。
- `extraction/heuristic.py`：
  - 标题/作者/年份/会议（版面推断，低置信度）；
  - 模型词表：HybridSN、SSRN、SpectralFormer、GCN、GAT、GraphSAGE、GIN、3D/2D-CNN、Transformer、ViT 等；
  - 模型家族映射；
  - 数据集词表：Indian Pines、Pavia、Salinas、Houston、Berlin、Botswana、Trento、MUUFL 等；
  - 图构建：KNN、RBF、dynamic、static、superpixel；
  - 指标：OA/AA/Kappa 正 + 反模式；
  - 训练比例、补丁尺寸、划分协议；
  - 所有 evidence 通过 `make_evidence_ref`。
- `extraction/llm.py`：
  - 严格 JSON Prompt；
  - 代码围栏/尾逗号修复；
  - Pydantic 风格逐字段校验；
  - 失败候选写入 `rejections`；
  - 缺 Key / 非 JSON / Provider 错误明确分类。
- `extraction/service.py`：模式解析、统一错误、证据计数。

### 关键 Bug 与修复

#### Bug 5：LLM 字段名不一致

Prompt 里方法是 `name`、数据集是 `name`、图构建是 `kind`，但校验函数只读 `value`，导致所有方法/数据集候选被静默当作“缺失”，且没有 rejection。

**修复**：`_field_from_candidate` 依次接受 `value` / `name` / `kind`；补充测试“有效候选通过”和“幻觉引文被拒绝”。

#### Bug 6：指标窗口过窄

最初 `_sentence_window` 遇到换行就截断，PDF 中“数据集 + 训练比例”常在上一行，导致指标无法关联条件。

**修复**：改为围绕匹配位置的连续字符窗口（260 字符），仍然是原文子串，可被核验；并在 note 中说明“文本窗口关联，不是表格解析”。

### 测试结果

- 规则抽取：标题/作者/年份/会议、GCN、HybridSN、Indian Pines、KNN/dynamic/RBF/static、OA/AA/Kappa、10%、9x9、random split 全部命中。
- 空白 PDF：所有字段 `null`，`missing_fields` 包含 `metadata.title`/`metrics`，提示需要 OCR。
- 幻觉：把 OA 值改成 `99.9%` 或伪造 quote，候选被丢弃并记录原因。
- 非法 JSON、缺 Key 均有明确错误。

---

## 3. P1-B：多论文对比

### 实现

- `compare.py`：
  - 方法行、数据集矩阵、指标行；
  - 可比组 `dataset|metric|train_ratio|patch_size|protocol`；
  - 至少 2 篇文档才排名；
  - 缺失条件 → `comparable=false` + 原因；
  - 单篇论文独有的指标不排名；
  - 单篇画像：优势/局限/适用场景（规则生成，明确标注）；
  - Markdown：概览、方法、数据集、指标、不可比项、画像、人工复核清单、证据附录。
- `/api/v1/compare` 持久化；`/compare/{id}.md` 下载。

### 测试结果

- Indian Pines + 10% + 9x9 + random split 的两条 OA 进入同组，排名 1/2；
- Kappa 只有一篇 → `comparable=false`，无排名；
- 缺训练比例 → `train_ratio_missing`，两条 OA 均不可比；
- 重复文档 ID → 422；不存在文档 → 404；
- LLM 模式无 Key → 503。

---

## 4. P1-C：引用核验

### 实现

- 本地引用语法 `[[doc:<id> p.<n> "quote"]]`；
- `audit_report`：
  - 文档/页码/原文/值；
  - 外部链接 `external_unchecked`；
  - 非法语法 `malformed`；
  - 数值性结论无引用 → `unsupported_claims`；
- 报告自动追加“引用核验报告”；
- 单条 `/api/v1/evidence/verify`；
- 页面点击引用 → 打开 PDF 页文本并高亮片段。

### 测试结果

- 通过 1 条、失败 3 条、外部 1 条、malformed 1 条、缺引用 1 条的单测；
- `verified_page_only` 与 `verified_quote` 明确区分；
- 表格行/标题不误报缺引用；
- 审计节幂等，不重复追加。

---

## 5. P2：混合 RAG

### 实现

- 页级 chunk（保留页码/字符偏移），不跨页；
- BM25（英文 token + 中文单字/二元组）；
- `HashEmbedder`（离线、词法哈希、明确非语义）；
- `OpenAIEmbedder`（真实 embedding，批次 + 重试）；
- 内存索引 + JSON 持久化（向量 base64 float32）；
- RRF + 加权融合 + 词法覆盖率重排；
- 空结果/低分拒答；
- 抽取式回答 / LLM 回答（无有效引用自动降级）；
- 引用审计复用 `citations.py`。

### 关键 Bug 与修复

#### Bug 7：`len(int)`

`index_documents` 里写成 `len(index.stats()["total_chunks"])`，`total_chunks` 是 int，工作流 `retrieve` 节点直接 `TypeError`。

**修复**：改为 `int(index.stats()["total_chunks"])`。

#### Bug 8：索引兼容状态

索引由不同 embedding 构建时 `compatible=false`；重建后没有恢复。**修复**：`save()` 时重置 `manifest_embedding` 与 `compatible=true`。

### 测试结果

- 2 篇 PDF、4 个 chunks 索引成功；
- 查询 `dynamic graph KNN Indian Pines` 首位命中正确；
- 回答 `grounded=true`，3 条引用全部通过；
- 空知识库拒答；
- 删除文献后 chunks 减少；
- OpenAI embedding 缺 Key → 503；
- 合成夹具 Recall@1/3、MRR = 1.0（仅流水线，不代表真实语义检索）。

---

## 6. P3：工作流与工程化

### 实现

- 7 节点 DAG：`plan → screen → retrieve → extract → verify → compare → report`；
- `WorkflowState` 保存文档、页文本、抽取结果、检索片段、对比、审计；
- `workflow_steps` 持久化节点状态/尝试/耗时/错误；
- 节点超时 + 有界重试；
- 幂等键；
- 统一 API 错误、Trace ID、限流、安全头、可选 API Key；
- 任务列表瘦身、PDF 去重、索引删除联动。

### 关键 Bug 与修复

#### Bug 9：工作流 `retrieve` 失败

由 Bug 7 引起；修复后 7/7 节点完成。

#### Bug 10：测试临时目录被沙箱拒绝

首次把测试工作区放到系统 `Temp`，Windows 沙箱对子目录 `mkdir` 返回 `WinError 5`。

**修复**：测试工作区改为项目内 `.test-workspace/`（Git 忽略），并在每个用例前带重试地清理。**没有跳过测试**。

#### Bug 11：SQLite / PDF 文件锁（见 P0 Bug 2/3）

修复后测试稳定。

---

## 7. 前端

- 单页、无构建步骤，保持 `web/index.html`；
- 五个页签：研究、文献库、对比、知识库、任务与工作流；
- 自写安全 Markdown 渲染（先转义再解析，支持表格/引用/代码块）；
- 本地引用变为可点击页码，打开 PDF 页文本并高亮片段；
- 研究任务轮询事件、状态、报告、引用审计；
- 文献上传/删除/查看/多选；
- 对比表、可比性徽章、不可比原因、Markdown 下载；
- KB 索引/检索/问答/拒答；
- 工作流节点时间线与报告；
- 任务历史。

### 未完成的视觉验证

尝试用 Chrome headless 截图：

```powershell
chrome --headless=new --screenshot=... http://127.0.0.1:8010/
```

失败原因：Windows 沙箱禁止 Chrome 的 Mojo 命名管道（`platform_channel.cc: Permission denied`），单进程模式也一样。

**已完成的替代验证**：

- `GET /` 返回 200，页面约 50 KB；
- 抽取内联 JS，`node --check` 通过；
- 所有 API 通过真实 Uvicorn + HTTP 冒烟。

**未完成**：浏览器视觉截图/交互自动化；README 使用结构示意图并明确标注，不伪造运行截图。

---

## 8. 真实运行记录

### 8.1 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

```text
.............................................................            [100%]
98 passed, 1 warning in 12.34s
```

### 8.2 Lint

```powershell
.\.venv\Scripts\ruff.exe check spectrascholar tests scripts
```

```text
All checks passed!
```

### 8.3 覆盖率

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=spectrascholar --cov-report=term
```

```text
TOTAL  4377 statements  657 missed  85%
```

### 8.4 合成夹具评测

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_pipeline.py
```

```text
Extraction field accuracy: 20/20 (1.0)
Evidence acceptance: 23/23 (1.0)
Retrieval [bm25]:   Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [vector]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [hybrid]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Citation validity: 1.0 (4 checks)
Workflow: completed 7/7 steps
Latency: compare 123ms, index 18ms, search median 3ms, answer 20ms, workflow 379ms
```

> 这些数字只来自三份合成 PDF（两篇正文 + 一张带线表格）+ hash 词法嵌入；三种检索模式并列，不能宣称混合检索提升。真实论文抽取已在 10.9 评测；真实检索/RAG 与真实 embedding 仍未验证。

### 8.5 HTTP 冒烟

启动：

```powershell
$env:WORKSPACE_DIR="$PWD\.smoke-workspace"
.\.venv\Scripts\python.exe -m uvicorn spectrascholar.main:app --host 127.0.0.1 --port 8010
```

实际结果：

- 上传 2 篇 PDF：201；
- Demo 研究：202 → completed，报告 623 字符，引用审计 0 条；
- 对比：200，OA 98.4% / 97.1% 可比，排名 1/2；Kappa 单篇不可比；
- 索引：200，4 chunks；
- 检索：命中 dynamic_gnn p.1；
- 问答：grounded=true，refusal=false，引用通过；
- 工作流：202 → completed，7/7 节点；
- 报告下载 / OpenAPI：200。
- 表格 HTTP 冒烟：上传带线表格 PDF → 对比返回 6 条 `source=table` 指标（HybridSN/GCN），Markdown 含“来源”列；
- 任务列表接口已瘦身：`GET /api/v1/research` 不返回 `report` 字段。

### 8.6 未验证事项

| 事项 | 原因 | 影响 |
|---|---|---|
| GPT Researcher 真实本地 PDF | 已用 DeepSeek 完成 10/10 | 报告均值 14.7k 字符；p50 24.0s；无页级引用 |
| GPT Researcher 真实网页检索 | 已完成 10/10（Tavily） | 均值 20.2k 字符、62 来源；代理环境需临时放行 |
| 真实 LLM 抽取 | 夹具 12/12；真实论文 3 篇已评测 | 文本表 + Tesseract OCR 绑定 21/24；OCR 仍有误读 |
| 真实论文评测 | 3 篇 PDF 已评测 | 只评抽取，不评真实检索/RAG |
| Docker 构建 | 本机通过 | Docker 29.9.2 + Compose 5.6.0；api healthy、worker completed；第二台机器未验证 |
| 浏览器截图 | Chrome IPC 被沙箱阻断 | UI 只做 HTTP/JS 语法验证 |
| 语义检索质量 | 默认 hash 嵌入 | 明确标注非语义，未宣称效果 |

---

## 9. 设计决策记录（ADR 摘要）

| 决策 | 选择 | 理由 | 代价 |
|---|---|---|---|
| 研究引擎 | 复用 GPT Researcher | 上游搜索/抓取/报告成熟；避免重造 | 版本兼容/外部依赖 |
| 数据模型 | 所有字段带 EvidenceRef | 可信性优先 | 代码更啰嗦 |
| 抽取默认 | heuristic | 离线可跑、无幻觉 | 表格/语义能力弱 |
| 对比 | 条件一致才排名 | 防止错误 SOTA 结论 | 很多数值显示“不可比” |
| RAG | 内存索引 + JSON | 单机、可解释、测试快 | 不适合大规模 |
| 工作流 | 自建状态机 | 固定 DAG、契约清晰 | 无 LangGraph 生态 |
| 任务执行 | BackgroundTasks | 本地演示简单 | 不适合生产并发 |
| 存储 | SQLite | 零运维、易复现 | 多用户/并发弱 |
| 前端 | 原生 HTML/JS | 不引入构建链 | 复杂交互需手写 |

---

## 10. 第二阶段：表格感知抽取与检索消融（本次新增）

### 10.1 为什么先做这个

真实论文的 OA/AA/Kappa 大量在表格里，而第一版只做正文文本窗口，容易出现“能读到数字但不知道属于哪个方法/数据集”的问题。本轮目标：

1. 用结构化表格解析补上**方法级指标**；
2. 不放松证据约束：表格数值仍要能在页文本中定位；
3. 建立 BM25 / 向量 / 混合三种检索模式的真实消融脚本；
4. 保持无 API Key 也能跑测试。

### 10.2 表格抽取实现

新增 `spectrascholar/extraction/tables.py`（235 行）：

- `pdfplumber>=0.11,<1` 的 `page.find_tables()` 检测带线表格；
- 表头识别：`OA`、`AA`、`Kappa`、`OA(%)`、`Overall Accuracy` 等别名；
- 行首识别为方法名，列识别为指标；
- 表格标题/上方 110pt 区域用于提取数据集、训练比例、补丁、协议；
- 表格数值必须仍能在 pypdf 页文本中找到，才生成 `verified_quote` 证据；
- `98.4/97.1`、`98.4 ± 0.2` 等多值单元格记录 `ambiguous_table_cell`，不猜测；
- 无表格、pdfplumber 未安装、PDF 打不开、开关关闭都自动降级并写 note；
- `MetricRecord` 新增 `method` 与 `source=table`；
- 与正文指标按 `(dataset, metric, value, page)` 去重，优先保留表格的行列关联，同时保留正文里已有的补丁/协议条件。

### 10.3 发现并修复的 Bug

#### Bug：多值单元格没有被拒绝

最初只拒绝“数字 + 字母”的单元格，`98.4/97.1` 没有字母，会被静默跳过，既没有指标也没有 rejection，难以审计。

**修复**：任何含数字但无法解析为单一数值的单元格都记录 `ambiguous_table_cell`，明确写入 `rejections`。

#### Bug：表格条件覆盖正文条件

表格指标替换正文同 key 指标时，最初直接丢掉正文已有的 `patch_size`。

**修复**：合并时表格字段优先，缺失字段回退到正文值；仍不猜测缺失协议。

### 10.4 表格夹具与测试

`tests/conftest.py` 现在生成**带真实 PDF 线条**的表格页：

```text
Table 1: OA on Indian Pines with 10% training samples, patch size 9x9, random split.
Method   OA     AA     Kappa
HybridSN 98.4   97.8   0.976
GCN      97.1   96.5   0.965
```

新增 `tests/test_tables.py` 5 个测试：

- 真实表格 PDF → 6 条 table 指标、方法 HybridSN/GCN、数据集/训练比例/补丁/协议、证据通过；
- `98.4/97.1` → ambiguous rejection；
- 页文本无数字 → quote_not_found；
- 无表格 / 开关关闭 / PDF 打不开 → 降级 note；
- 表格指标与正文合并、`source=table` 展示；
- API 对比返回 `source=table`、方法列、Markdown “来源”列。

### 10.5 检索消融

`scripts/evaluate_pipeline.py` 现在对同一组标注查询分别运行：

- `bm25`
- `vector`
- `hybrid`

实际结果（hash-512，合成三文档）：

```text
Retrieval [bm25]:   Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [vector]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [hybrid]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
```

**结论**：三者并列，不能宣称混合检索更好。原因是语料只有 3 篇/约 8 chunks，查询与标注高度重合，且 hash 嵌入本身就是词法哈希。要证明语义收益，必须换真实 embedding 和更难的真实论文查询。这一点已写入 README/EVALUATION，避免误导。

### 10.6 本轮真实结果

```text
pytest -q                         → 98 passed
pytest --cov                      → 85% (4377 / 657)
ruff check                        → All checks passed
Extraction field accuracy         → 20/20
Evidence acceptance               → 23/23
Citation validity                 → 4/4
Workflow                          → 7/7
```

### 10.7 DeepSeek 支持（补充）

上游源码确认：`gpt_researcher/llm_provider/generic/base.py` 内置 `deepseek` provider，使用 `ChatOpenAI(openai_api_base="https://api.deepseek.com", openai_api_key=os.environ["DEEPSEEK_API_KEY"])`。因此 DeepSeek 可以驱动 GPT Researcher 的聊天/报告流程。

本轮补充：

- 新增 `spectrascholar/llm_config.py`：统一解析 `OPENAI_API_KEY` 或 `DEEPSEEK_API_KEY`，供 LLM 抽取和 RAG 问答共用；OpenAI 优先。
- `GPTResearcherBackend._preflight` 按 provider 检查对应密钥（`openai`→`OPENAI_API_KEY`，`deepseek`→`DEEPSEEK_API_KEY`）。
- 只配置 DeepSeek 时，settings 自动把 GPT Researcher / 抽取 / 问答模型切到 `deepseek-chat`。
- 在每任务 GPT Researcher 配置中加 `CONTEXT_FILTER=keyword`，避免 DeepSeek-only 环境隐式调用 OpenAI embedding。
- **限制**：DeepSeek 没有官方 embedding API。`EMBEDDING_BACKEND=openai` 不能指向 DeepSeek；默认保持 `hash`，或在 `.env` 配置其他 OpenAI 兼容 embedding 服务。
- 新增 4 个 `test_llm_config.py` 测试 + 1 个 GPT Researcher DeepSeek provider 测试。
- 当前沙箱仍无法访问 `api.deepseek.com`，所以只完成代码、单元测试和上游源码核对，**没有真实 DeepSeek 调用**。

### 10.8 真实 DeepSeek / GPT Researcher 联调（2026-10-20）

用户提供 DeepSeek Key 后完成了真实调用：

1. **聊天冒烟**：`deepseek-chat` 返回 `OK`，usage 10 tokens；服务端返回的 model 字段是 `deepseek-flash`，不影响调用。
2. **真实 LLM 抽取**：两页夹具，`12/12` 候选通过逐字核验；OA 98.4%、Kappa 0.977；约 3.7s。指标的数据集/方法关联仍缺失，不能直接排名。
3. **真实 RAG 回答**：3 条 page-only 引用，`grounded=false`；回答把引用放在段末，未逐句附引用，审计保持严格。
4. **真实 GPT Researcher API 任务**（`source=local`）：
   - 第 1 次：completed，15,263 字符，28,770 ms，`backend=gptr`、`is_demo=false`；
   - 第 2 次：completed，14,861 字符，32,411 ms；
   - 这两次只读本地合成 PDF；真实网页检索在后续第 6 点完成 10 次。
5. **10 任务可靠性评测**（2026-10-21，`scripts/evaluate_research.py`）：
   - 10/10 completed，成功率 1.0；
   - 报告均值 14,742 字符；p50 23,993 ms，p95 33,529 ms；
   - 上游 `costs` 合计 0.663485（上游估算，不是账单）；
   - 引用标记 301 条：页级通过 0、本地 PDF 文件链接 255、外部链接 46、缺引用数值结论 88；
   - 结果写入 `docs/research_runs.json` / `docs/research_runs.md`；
   - 这是任务可靠性评测，不是真实论文质量评测。
6. **真实网页检索（Tavily，10 次）**（2026-10-21）：
   - Tavily `/search` 返回 HTTP 200、3 条结果；
   - 首次完整网页研究因当前网络把公网域名解析到 `198.18.0.x`，被上游 SSRF 防护判为内网，`empty_context` 失败；
   - 仅对本次进程设置 `ALLOW_PRIVATE_URLS=true` 后成功；
   - 新增 `scripts/evaluate_web_research.py`，跑 10/10 completed；
   - 报告均值 20,179.5 字符；p50 36,861 ms、p95 42,714 ms；62 个来源；costs 合计 1.078075；
   - 审计：443 条外部链接未核验、页级通过 0、31 条数值结论缺引用；
   - 结果写入 `docs/web_research_runs.json` / `docs/web_research_runs.md`；
   - **不是生产稳定性结论**；`ALLOW_PRIVATE_URLS=true` 关闭 SSRF 防护，不能用于生产。

联调中发现并修复的 Bug：

- **`config_dir` 未创建**：`scripts/smoke_gptr.py` 直接调用 backend 时，`_write_config` 写文件失败。修复：写入前 `mkdir(parents=True, exist_ok=True)`，smoke 脚本调用 `settings.ensure_directories()`。
- **smoke 回调参数不匹配**：`on_event` 缺少 `duration_ms` 默认值，`TypeError`。修复为可选参数。
- **空环境变量覆盖模型默认值**：用户 `.env` 中 `EXTRACTION_MODEL=` 等空字符串会覆盖 settings 的 DeepSeek 默认值，导致模型名为空。修复：所有模型字段使用 `os.getenv(...).strip() or default`。
- **测试读取真实 `.env`**：用户加入 Key 后，pytest 可能加载真实 Key。修复：新增 `SPECTRASCHOLAR_SKIP_DOTENV=1`，conftest 在导入 app 前设置，测试永不读取真实 `.env`。
- **上游报告引用格式不可页级核验**：GPT Researcher 使用 `[filename](xxx.pdf)` 或作者-年份，不是 `[[doc:id p.N]]`。修复：新增 `local_file_unverified` 状态与统计，识别相对 PDF 链接；审计明确写“未做页级核验”，不把链接当已验证。
- **段末引用误报**：`"OA 98.4%。[[doc:d1 p.1]]"` 的引用标记被拆成独立句，导致数值句误报缺引用。修复：将 marker-only 片段合并到上一句。
- **真实运行元数据未持久化**：任务详情拿不到 `costs/sources/elapsed`，评测无法记录成本。修复：`jobs.metadata` 列 + `JobDetails.metadata`，`finish_job` 保存上游元数据。
- **评测脚本与测试工厂耦合**：`tests/conftest.py` 导入即设置测试工作区/跳过 `.env`，无法用于真实评测。修复：新增无副作用 `tests/pdf_factory.py`，评测脚本单独使用。

真实结果边界：

- 真实 web 检索完成 10/10，但需要代理放行；外部链接未核验，不能宣称“引用正确”或生产可用；
- 上游报告没有页级引用，所以“引用核验通过”仍为 0；
- 3 篇真实论文已完成抽取评测；2 份中文精读笔记被排除在准确率分母之外。

### 10.9 真实论文抽取评测（P4.3，3 篇）

工作区提供 3 篇英文原论文（HybridSN、SSRN、WFCG）和 2 份中文精读笔记。后者只做“非论文输入”
鲁棒性对照，不进入准确率分母。人工标注 24 条指标、8 个实验条件、9 个数据集字段。

| 指标 | heuristic | LLM（DeepSeek） |
|---|---|---|
| title | 0/3 | 3/3 |
| year | 3/3 | 3/3 |
| venue | 2/3 | 3/3 |
| 主方法 | 2/3 | 3/3 |
| 数据集 | 8/9 | 9/9 |
| 实验条件 | 0/8 | 5/8 |
| 指标数值 | 12/24 | 21/24 |
| 指标→数据集绑定 | 12/24 | **21/24** |
| 指标→比例/patch 绑定 | 0/24 | **9/24** |
| 证据接受率 | 168/168 | 271/277 |

关键发现：

- LLM 对元数据/方法/数据集很强；
- 文本表格行解析 + Tesseract OCR 转置表解析后，指标→数据集从 0/24 提升到 **21/24**；
- SSRN/WFCG 的图片表已真实 OCR，但仍存在 OCR 误读、列错位和表题缺失；不能把 21/24 写成“完整正确”；
- heuristic 借文本行解析拿到 HybridSN 指标，但条件化仍为 0/24；图片表无效；
- 证据接受率高只说明引文存在，不证明引文支持数值或实验条件。

结果文件：`docs/real_paper_runs.json`、`docs/real_paper_runs.md`；
标注：`eval/real_papers.labels.json`；脚本：`scripts/evaluate_real_papers.py`。

### 10.10 V1.5 SQLite 队列与 V1.4 对照报告

- 新增 `spectrascholar/job_queue.py`：`BEGIN IMMEDIATE` 认领、stale lock 恢复、独立 worker。
- API 默认可用 `QUEUE_BACKEND=sqlite`；测试用 `inline` 保持旧路径。
- 跨进程验收：API 提交后进程退出 → `scripts/run_worker.py --once` 认领 → completed。
- 新增 `scripts/generate_real_comparison.py`：3 篇真实论文、46,987 字符报告、82 个页级引用、0 个可比组（不强行排名）。
- Dockerfile 复制 `scripts/`，compose 增加 `worker` 服务；当时无 Docker CLI，未构建。

### 10.11 仍未完成

- 继续修正 SSRN/WFCG 的 OCR 列错位/表题缺失；当前真实 OCR 后指标绑定 21/24，仍不能宣称完整；
- 真实论文上的检索/RAG 评测（P4.3 只评抽取）；
- 无代理放行/生产网络下的 web 稳定性评测；
- 真实 embedding 的 ablation；
- Docker Compose 真实构建与第二台机器验证。

### 10.12 V2.1：arXiv Tool Calling

新增：

- `spectrascholar/tools/arxiv_search.py`：关键词转 `all:`、年份 `submittedDate`、主题拆词、DOI/arXiv ID 去重、分页、重试；
- `spectrascholar/api/tools.py`：`GET /api/v1/tools/arxiv_search`，`asyncio.to_thread` + 硬超时；
- 5 个离线测试，假客户端覆盖查询构造、DOI 去重、空结果、端点、缺依赖。

真实调用（2026-10-21）：

```text
query=hyperspectral graph neural network
year=2020–2026
task_topic=hyperspectral classification
returned=3 attempts=1 duplicates=0
```

返回 3 篇相关论文（含 2024/2025/2026）。工具端点已通过 `WorkflowRequest.tools=["arxiv_search"]` 接入 `plan` 节点；这是显式调用，不是 LLM 自主选择。

### 10.13 V1.6：Docker 本机验证

环境：Docker Desktop 29.9.2、Compose v5.6.0、WSL 3.0.3.0 / kernel 6.18.54.1-1。

```text
docker compose build       -> 成功
docker compose up -d       -> api healthy, worker running
POST /api/v1/research      -> 202 queued, demo=true
worker                     -> claimed ... / finished ...: completed（949 ms，1,219 字符）
docker compose down        -> 清理
```

注意：构建时 `docker-credential-desktop` 不在 PATH，需先把 `D:\Docker\resources\bin` 加入 PATH。  
这是本机容器验证；第二台电脑仍未验证。

### 10.14 工具接入工作流

`WorkflowRequest` 新增：

```text
tools=["arxiv_search"]
arxiv_year_from / arxiv_year_to
arxiv_max_results
```

`plan` 节点在 `tools` 显式包含 `arxiv_search` 时调用工具：

- 记录 `tool_calls`（参数/状态/返回数/错误）；
- 保存 `arxiv_results`（标题/年份/DOI/URL）；
- 报告中增加“外部工具调用（arXiv）”；
- 工具失败/超时不阻塞本地 PDF 流程，不伪造结果；
- 外部结果不进入本地证据链，也不参与可比组/排名。

这是**显式工具调用**，不是 LLM 自主选择。

2026-10-22 真实 workflow 验证（两篇本地 PDF）：workflow 完成，`arxiv_search` 因网络超时写入 `status=failed`，报告仍生成；离线假客户端覆盖成功路径。

### 10.16 取消 / 预算 / 队列可靠性

新增：

- `POST /api/v1/research/{job_id}/cancel`：
  - queued：立即改 jobs + job_queue 为 cancelled；
  - running：设置 `cancel_requested=1`，worker 在阶段边界协作取消；
  - 已完成/失败/已取消返回 409。
- `ResearchRequest.max_elapsed_seconds`：总时间预算，且受 `RESEARCH_TIMEOUT_SECONDS` 上限约束；
- `ResearchRequest.max_cost_usd`：上游返回 `costs` 后检查，超预算标记 `budget_exceeded`，不保存成功报告；
- `job_queue.mark_done` 不覆盖 cancelled；
- `finish_job` 不用 late worker 结果覆盖 cancelled；
- `mark_job_running` 不把 cancelled 改回 running；
- worker 在领取后、执行后都检查取消标记。

这是**协作式取消**：已进入不可中断的上游网络调用时，只能在阶段边界停止；不声称硬杀进程。

### 10.15a 自主 Tool Calling 循环（V2.2）

新增 `spectrascholar/agent/tool_loop.py` 与 `POST /api/v1/tools/agent_loop`：

- 有界 planner，最多 5 步；
- 工具白名单：`arxiv_search`、`local_search`；
- 每步 observation，工具失败不无限重试；
- 到上限强制收尾；
- 真实 DeepSeek planner + `local_search` 已跑通（1 步，max_steps 收尾）；
- 离线测试覆盖工具调用→finish、非法工具、步数上限、API 响应。

真实 embedding：

- `scripts/evaluate_retrieval.py --embedding openai` 已接入 `OpenAIEmbedder`；
- 本机缺 `OPENAI_API_KEY`，返回 `REAL_EMBEDDING_BLOCKED`，不覆盖 hash 基线；
- 不能把 hash 结果写成真实语义检索。

### 10.15 真实检索评测与 Claim-level 核验

新增：

- `eval/research_eval.json`：30 条真实论文检索题，gold 为 document/page/quote；
- `scripts/evaluate_retrieval.py --ocr`：BM25 / hash / hybrid RRF 的 Recall@1/3/5 与 MRR；索引时追加可选 OCR 表格文本；
- `citations.py` 的 `audit_claims`：逐句映射 supported_quote / page_only / external_unchecked / no_citation / citation_failed；
- `CitationAudit` 新增 claim 计数字段，报告自动附加 claim-level 统计。

真实基线：

```text
Answer-level:
BM25   Recall@5 36.7%  MRR@5 0.206
hash   Recall@5 46.7%  MRR@5 0.342
hybrid Recall@5 40.0%  MRR@5 0.248
严格 page-level:
BM25/hash/hybrid Recall@5 33.3%/30.0%/30.0%
```

说明：

- PDF 索引会追加可选 OCR 文本，图片表中的 WFCG/SSRN 数值可被检索；
- 新增 `rag/table_meta.py`：检测 TABLE/数据集/OA/AA/Kappa/训练比例/patch，并对候选页做确定性 boost；
- Answer-level 允许命中“包含 gold answer 的另一页”，page-level 仍要求精确 gold page；
- 严格 page-level 从上一轮的 30.0/23.3/26.7 变为 33.3/30.0/30.0：BM25/hash 提升，hybrid 仍低于最初 33.3% 基线；没有全面胜出；
- 基线仍偏低，不能宣称语义检索提升；hash 仍是词法哈希；
- Claim-level 只证明引文可追溯/句子有引用，不证明语义蕴含。

---

## 11. 下一步

1. 继续修正 SSRN/WFCG 的 OCR 列错位/表题缺失；目标把指标→数据集绑定从 21/24 继续提升。
2. 将 arXiv 工具接入工作流规划节点，形成真正的 tool-calling 循环。
3. 在 3 篇真实论文上做检索/RAG 评测（Recall@K、引用有效性、回答 grounded）。
4. 在第二台机器验证 Compose（本机已 build/up/worker 通过）。
5. OpenAI embedding 对照 hash，做真实 ablation。
6. 多级表头/跨页表/OCR。
7. Redis/RQ 队列与取消/预算。
8. 多用户与 PostgreSQL/pgvector。
9. 生成真实界面截图与 3 分钟演示视频。

---

## 12. Git / GitHub 发布状态

- 本地 Git 已初始化，按功能拆成多个功能/文档提交，当前分支 `main`，工作区干净。
- 远程已配置：
  ```text
  origin https://github.com/Zhang-J1a/SpectraScholar.git
  ```
- 用户已确认仓库为 **Private**。
- 推送尝试：
  - 默认 Schannel：`schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS`；
  - SSH：`kex_exchange_identification: Connection closed by remote host`；
  - 改用 OpenSSL 后能进入认证阶段，但非交互环境没有可用凭据：`could not read Username for 'https://github.com'`。
- 结论：**当前沙箱无法完成认证/推送**，代码只在本地提交；没有强推、没有覆盖远程、没有删除历史。
- 在有凭据的终端执行：
  ```powershell
  cd SpectraScholar-Starter
  git remote -v
  git push -u origin main
  ```
  若远程仓库尚未创建，先在 GitHub 创建私有仓库 `SpectraScholar`，再执行上述 push。

