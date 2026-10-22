# V1 验收记录（严格按路线）

日期：2026-10-21  
路线：[`../SpectraScholar_个人Agent改造路线.md`](../SpectraScholar_个人Agent改造路线.md)

## 结论

**V1 的 6 项中：4 项完成，2 项部分完成（V1.3 OCR、V1.6 第二台机器）。**

本机 Docker 已完成真实 `build/up`、api healthy、worker completed；但路线要求“另一台电脑”，这一步仍未验证。因此不能写“V1 全部通过”；可以写“V1 代码闭环 + 本机 Docker 通过；第二台机器和完整 OCR 绑定仍未完成”。

| V1 项 | 状态 | 证据 |
|---|---|---|
| 1. 10 个真实任务 | ✅ 完成 | 本地 PDF 10/10；Tavily 网页 10/10；成功率、失败、耗时、成本已记录 |
| 2. PDF 按页 page/document ID | ✅ 完成 | 页级证据、引用审计、`[[doc:id p.N "quote"]]` |
| 3. 表格解析 + 缺失字段 null/原因 | ⚠️ 部分 | 文本表 + Tesseract OCR 后绑定 21/24；OCR 仍有误读/列错位，未达到完整正确 |
| 4. 引用逐条映射 + citation_verified/unsupported | ✅ 结构化报告完成 | 3 篇真实论文对照，82 个页级引用、91 个页码；无可比组时 0 排名 |
| 5. 长任务可靠队列 | ✅ 完成 | SQLite queue + 独立 worker；跨进程验收 queued→completed |
| 6. Docker Compose 另一台电脑验证 | ⚠️ 本机通过，跨机器未验证 | Docker 29.9.2 + Compose v5.6.0；`compose build`、`up -d`、api healthy、worker completed 一次 Demo；第二台机器未验证 |

## V1 验收报告

> V2.1 额外完成：`/api/v1/tools/arxiv_search`，真实调用返回 3 条；已通过 `WorkflowRequest.tools=["arxiv_search"]` 接入 `plan` 节点，但仍是显式工具选择，不是 LLM 自主决策。真实 workflow 验证中 arXiv 网络超时，失败被记录且未阻塞本地流程；成功路径由离线测试覆盖。

- [真实论文结构化对照](real_paper_comparison.md)：3 篇论文、46,987 字符、82 个 `[[doc:... p.N "quote"]]`、91 个页码引用。
- [对照摘要](real_paper_comparison.json)：`comparable_groups=0`，说明没有在条件不一致时强行排名。
- [真实论文抽取评测](real_paper_runs.md)：LLM title/year/venue/method 3/3、datasets 9/9、指标数值 21/24、指标→数据集绑定 **21/24**、条件化绑定 **9/24**。
- [真实研究任务评测](research_runs.md)：10/10 completed。
- [真实网页评测](web_research_runs.md)：10/10 completed。

## V1.5 队列跨进程验收

```text
API 提交 → 202 queued
API 进程退出
scripts/run_worker.py --once
claimed ... (attempt 1)
finished ...: completed
queue_stats={'completed': 1}
```

这证明任务不再依赖 FastAPI `BackgroundTasks`；worker 崩溃后，超过 `QUEUE_LOCK_TIMEOUT_SECONDS` 的 running 行可被重新认领。

启动：

```powershell
# 终端 1
.\.venv\Scripts\python.exe -m uvicorn spectrascholar.main:app --port 8000
# 终端 2
.\.venv\Scripts\python.exe scripts\run_worker.py
```

## V1.3 仍需说明的边界

- HybridSN 的结果表是**文本行**，行解析器按表头把 9 个值绑定到 3 个数据集 × OA/Kappa/AA；仅文本表时是 12/24，加入 OCR 后提升到 21/24。
- SSRN/WFCG 的结果表主要是**图片**；Tesseract 5.5.3 已安装，OCR 已真实运行，并新增转置表解析（方法列 × OA/AA/Kappa 行）。
- 现实结果：指标→数据集绑定从 12/24 提升到 **21/24**，但仍有 OCR 误读、表题/列错位；**不满足“所有真实论文表格都稳定解析”**。
- 图片表 OCR 指标必须人工抽样核对，不能把 21/24 写成全对。

## V1.6 本机 Docker 验收

环境：

```text
Docker Desktop 29.9.2
Docker Compose v5.6.0
WSL 3.0.3.0 / kernel 6.18.54.1-1
```

真实执行：

```text
$env:PATH="D:\Docker\resources\bin;$env:PATH"  # docker-credential-desktop
docker compose build       -> api/worker 镜像构建成功
docker compose up -d       -> api healthy, worker running
POST /api/v1/research      -> 202 queued, demo=true
worker log                 -> claimed <job> (attempt 1)
                           -> finished <job>: completed
docker compose down        -> 容器/网络清理
```

任务耗时 949 ms，报告 1,219 字符。  
这证明 compose 的 `api + worker` 和共享命名卷在本机可用；但**没有在第二台电脑验证**，所以 V1.6 只能写“本机通过”，不能写“跨机器通过”。

## 下一步（严格顺序）

1. 在第二台电脑执行 `docker compose build && docker compose up -d`，验证跨机器部署。
2. 继续修正 OCR 列错位/表题缺失；当前指标绑定 21/24，仍不能宣称完整正确。
3. 若要继续 V2，再做 30–50 题评测集与真实 embedding ablation。
