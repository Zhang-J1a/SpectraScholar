# V1 验收记录（严格按路线）

日期：2026-10-21  
路线：[`../SpectraScholar_个人Agent改造路线.md`](../SpectraScholar_个人Agent改造路线.md)

## 结论

**V1 的 6 项中：3 项完成，1 项部分完成，1 项工程实现完成但部署未验证，1 项被环境阻塞。**

因此不能写“V1 全部通过”；可以写“V1 代码闭环完成，Docker/第二台机器验证未完成；图片表格 OCR 已真实运行，但仍有误读/列错位”。

| V1 项 | 状态 | 证据 |
|---|---|---|
| 1. 10 个真实任务 | ✅ 完成 | 本地 PDF 10/10；Tavily 网页 10/10；成功率、失败、耗时、成本已记录 |
| 2. PDF 按页 page/document ID | ✅ 完成 | 页级证据、引用审计、`[[doc:id p.N "quote"]]` |
| 3. 表格解析 + 缺失字段 null/原因 | ⚠️ 部分 | 文本表 + Tesseract OCR 后绑定 17/24；OCR 仍有误读/列错位，未达到完整正确 |
| 4. 引用逐条映射 + citation_verified/unsupported | ✅ 结构化报告完成 | 3 篇真实论文对照，82 个页级引用、91 个页码；无可比组时 0 排名 |
| 5. 长任务可靠队列 | ✅ 完成 | SQLite queue + 独立 worker；跨进程验收 queued→completed |
| 6. Docker Compose 另一台电脑验证 | ❌ 阻塞 | 当前机器无 `docker`/`podman`；compose 已加 worker，但未真实构建 |

## V1 验收报告

- [真实论文结构化对照](real_paper_comparison.md)：3 篇论文、46,987 字符、82 个 `[[doc:... p.N "quote"]]`、91 个页码引用。
- [对照摘要](real_paper_comparison.json)：`comparable_groups=0`，说明没有在条件不一致时强行排名。
- [真实论文抽取评测](real_paper_runs.md)：LLM title/year/venue/method 3/3、datasets 9/9、指标数值 18/24、指标→数据集绑定 **17/24**、条件化绑定 **6/24**。
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

- HybridSN 的结果表是**文本行**，新增的行解析器可以按表头把 9 个值绑定到 3 个数据集 × OA/Kappa/AA；因此从 0/24 提升到 12/24。
- SSRN/WFCG 的结果表主要是**图片**；Tesseract 5.5.3 已安装，OCR 已真实运行，并新增转置表解析（方法列 × OA/AA/Kappa 行）。
- 现实结果：指标→数据集绑定从 12/24 提升到 **17/24**，但仍有 OCR 误读、表题/列错位；**不满足“所有真实论文表格都稳定解析”**。
- 图片表 OCR 指标必须人工抽样核对，不能把 17/24 写成全对。

## V1.6 阻塞

```text
docker  = not found
podman  = not found
tesseract = not found
```

`compose.yaml` 已静态解析为 `api` + `worker` 两个服务，且 worker 共享 workspace 卷；但没有 Docker CLI，无法真实构建，更无法在“另一台电脑”验证。不能把静态 YAML 检查写成部署成功。

## 下一步（严格顺序）

1. 在有 Docker 的机器上执行 `docker compose up --build`，跑通 API + worker + 上传/研究/报告。
2. 安装 OCR（RapidOCR 或 Tesseract）后，为 SSRN/WFCG 图片表格补表格行绑定。
3. 继续修正 OCR 列错位/表题缺失；当前指标绑定 17/24，仍不能宣称完整正确。
4. 若要继续 V2，再做 30–50 题评测集与真实 embedding ablation。
