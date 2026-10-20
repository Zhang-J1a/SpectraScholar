# SpectraScholar — 个人科研 Agent 二次开发参考工程

> 项目类型：个人学习与 AI Agent 实习作品的**参考起点**，不是已经上线的生产系统。
> 研究引擎：通过独立 Adapter **集成 GPT Researcher**（Apache-2.0）；本文档及其余 `spectrascholar/` 是自建示例模块。

## 你能获得什么？

- **完整的个人工程边界**：FastAPI 后端、SQLite 任务记录、简单网页、PDF 管理、结构化论文比较、单元测试、Docker。
- **真实研究接口**：`GPTResearcherBackend` 调用 `GPTResearcher.conduct_research()` 和 `write_report()`；需要额外安装和配置 API 服务。
- **不会伪造检索结果的离线 Demo**：默认 `RESEARCH_BACKEND=demo`，演示请求、任务状态、报告下载，但明确标注没有使用搜索或 LLM。
- **论文比较的离线基线**：`EXTRACTOR_BACKEND=heuristic` 只从 PDF 文本里抓取少量已知数据集的字面出现，不会虚构 OA/AA/Kappa。
- **可选 LLM 提取**：将结构化候选与 PDF 页码和连续原文片段核对；失败的候选丢弃。**原文出现 ≠ 事实可信 ≠ 实验可比**。

## 当前交付的实现范围

| 功能 | 状态 |
|---|---|
| FastAPI API / 自动 `/docs` | 已编写，可离线运行 |
| 浏览器界面 / PDF 上传 | 已编写 |
| SQLite 任务与历史 / Markdown 报告下载 | 已编写 |
| GPT Researcher 真正对接入口 | 已编写 Adapter，**尚未在当前环境验证真实 API 成功调用** |
| PDF 提取 / 数据集关键词基线 | 已编写并有离线测试 |
| LLM 结构化抽取 + 原文匹配验证 | 已编写，**模型 API 效果尚未实测** |
| 生产级任务队列、多租户鉴权、知识库向量索引 | 尚未开发 |
| 稳定的论文表格解析、精度指标对齐、完整 Eval 集 | 尚未开发 |

## 1 分钟体验（离线 Demo）

前提：Python 3.12 推荐，Windows PowerShell：

```powershell
cd SpectraScholar-Starter
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn spectrascholar.main:app --reload
```

Linux/macOS：

```bash
cd SpectraScholar-Starter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn spectrascholar.main:app --reload
```

打开：

- 页面：http://127.0.0.1:8000/
- OpenAPI：http://127.0.0.1:8000/docs
- 状态检查：http://127.0.0.1:8000/api/v1/health

演示模式会返回明确标注的虚拟完成状态消息，不会冒充真实调研结果。

## 切换真实 GPT Researcher（需联网和付费/限额 API）

```bash
pip install -r requirements-live.txt
```

修改 `.env`：

```dotenv
RESEARCH_BACKEND=gptr
OPENAI_API_KEY=你的有效Key
TAVILY_API_KEY=你的有效搜索Key
# 可选：只在你使用的兼容 API 支持该地址与模型设置时配置
OPENAI_BASE_URL=
```

在项目目录重新执行：

```bash
uvicorn spectrascholar.main:app --reload
```

如果要查询本地论文，请先上传 PDF，然后将「资料来源」设为 `local`。`DOC_PATH` 默认指向 `workspace/papers/`。具体搜索工具、模型配置、兼容性与计费以 GPT Researcher 上游文档为准。不同模型供应商可能需要配置 GPT Researcher 自身的额外选项。

**注意**：本工程仅使用了 GPT Researcher 的研究 API，未复制其前端和完整实现；原项目不是本项目的个人原创贡献。

## PDF 多论文比较

1. 在页面上传 2～5 篇可正常提取文字的 PDF。
2. 勾选论文，点击「比较选中论文」。
3. 默认只返回可以字面确认的已知数据集名称及页码。
4. 如果配置了兼容模型 API，可以在 `.env` 设置 `EXTRACTOR_BACKEND=llm`，提取方法名称、数据集及 OA 等指标的候选值，并进行**精确原文片段核验**。
5. 论文表格可能提取不全；**不能把相同数据集不同训练比例下的 OA 直接比较**。

## API 说明

| 方法 | 地址 | 用途 |
|---|---|---|
| GET | `/api/v1/health` | 服务与运行模式 |
| POST | `/api/v1/research` | 提交后台研究任务 |
| GET | `/api/v1/research` | 最近任务 |
| GET | `/api/v1/research/{id}` | 任务状态/报告 |
| GET | `/api/v1/reports/{id}.md` | 下载报告 |
| POST | `/api/v1/documents` | 上传 PDF |
| GET | `/api/v1/documents` | 列出已上传文件 |
| POST | `/api/v1/compare` | 论文对比 |

请求样例：

```json
{"topic":"比较高光谱图分类中的动态图方法和静态图方法","source":"web","domain":"hyperspectral","language":"zh"}
```

## 目录

```text
SpectraScholar-Starter/
├── spectrascholar/
│   ├── main.py         # FastAPI 路由、上传、任务接口
│   ├── schemas.py      # Pydantic 数据契约
│   ├── settings.py     # 单一配置入口
│   ├── domains.py      # 业务 Prompt / 可替换领域模板
│   ├── research.py     # GPT Researcher Adapter / DemoAdapter
│   ├── evidence.py     # PDF 读取、结构化抽取、原文匹配核验
│   └── store.py        # SQLite 任务/文档持久化
├── web/index.html      # 可替换的极简网页
├── tests/              # 离线自动化测试
├── scripts/            # 评测辅助脚本
├── docs/               # 改造清单 / Codex 提示词 / 架构和面试材料
├── workspace/          # 上传文件、研究记录，已被 Git 忽略
├── .env.example
├── requirements*.txt
├── compose.yaml
└── Dockerfile
```

## 测试与 Docker

```bash
pip install -r requirements-dev.txt
pytest -q
```

```bash
# 项目目录下
cp .env.example .env
# offline demo (does not install GPT Researcher by default)
docker compose up --build
```

需要构建包含 GPT Researcher 的镜像时：

```bash
INSTALL_GPT_RESEARCHER=1 docker compose build --no-cache
# .env RESEARCH_BACKEND=gptr + valid API secrets
docker compose up -d
```

PowerShell 构建可先执行 `$env:INSTALL_GPT_RESEARCHER="1"`，再执行 `docker compose build`。

## 现实边界与下一步

目前背景任务使用 FastAPI `BackgroundTasks`，仅适合本地演示和低并发。生产环境应改为 Celery/RQ + Redis/数据库，提供取消/重试/超时、并发限制和计费预算。上传文件在公开服务必须增加鉴权、恶意 PDF 检查、速率限制、隔离工作目录。`/api/v1/research/{id}` 包含完整报告与异常，部署到公网前必须增加用户权限隔离并清理敏感日志。

按照 `docs/ROADMAP.md` 完成第二阶段以后再尝试求职简历包装；任何简历指标都必须以测试实际结果为准。

## 开源归属

- 上游研究引擎：<https://github.com/assafelovic/gpt-researcher>，**Apache License 2.0**。
- 本项目示例代码独立组织，通过 Python 包接口调用上游依赖。请保留上游来源说明。
- 若后续复制/修改上游源码或分发其衍生代码，请同时履行上游 LICENSE / NOTICE / 修改说明要求。
- 更换领域、Prompt 和网页标题本身不构成完整个人研发贡献；请用自己的工作成果、Git 提交和评测证明贡献。
