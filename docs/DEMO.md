# 3 分钟演示脚本

> 演示前先启动服务。所有数字应以你本机实际运行结果为准；不要照抄文档中的合成夹具分数当真实论文结果。

## 1. 启动（离线）

```powershell
cd SpectraScholar-Starter
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
uvicorn spectrascholar.main:app --reload
```

打开 <http://127.0.0.1:8000/>。

生成三份合成演示 PDF（两篇正文 + 一张带线表格，可选）：

```powershell
python scripts\make_demo_pdfs.py --out demo_assets
```

## 2. 演示路径

### 2.1 运行模式（10 秒）

顶部徽章应显示：

- 研究引擎：`demo`（黄色，明确非真实检索）
- 抽取：`heuristic`
- 嵌入：`hash`（黄色，明确非语义）
- API Key 鉴权：关

讲解：**这三种“黄色”是诚实边界，不是缺陷**。设置 Key 后可切到真实模式。

### 2.2 文献库（30 秒）

1. 上传 `demo_assets/dynamic_gnn.pdf`、`hybridsn.pdf` 与 `table_paper.pdf`。
2. 指出：文件名、页数、大小、SHA 前 10 位、标题。
3. 再上传同一文件 → 返回已有记录（SHA 去重）。
4. 点“查看” → 打开 PDF 页文本。

### 2.3 论文对比（45 秒）

1. 勾选三篇 → “比较选中论文”。
2. 展示：
   - 方法/模型家族/图构建；
   - 数据集矩阵；
   - 指标表新增“来源”列：`table_paper.pdf` 的 6 条指标显示 `source=table`，方法列为 HybridSN/GCN；
   - OA 98.4% vs 97.1%，训练比例 10%、补丁 9x9、协议随机 → **可比**，排名 1/2；
   - Kappa 只有部分论文报告 → **不可比**，无排名；
   - “不可比项与风险提示”。
3. 下载 Markdown，指出证据附录的页码和引用。

### 2.4 工作流（45 秒）

1. 勾选三篇 → “运行本地工作流”。
2. 展示 7 个节点：plan/screen/retrieve/extract/verify/compare/report。
3. 每个节点有状态、尝试次数、耗时、输出摘要。
4. 打开工作流报告：包含引用核验报告与工作流边界说明。

### 2.5 知识库（40 秒）

1. “索引全部文献” → 显示 4 chunks（合成夹具）。
2. 提问：“What accuracy does the dynamic graph method report on Indian Pines?”
3. 展示抽取式回答 + `[[doc:... p.N]]` 引用；点页码打开原文页并高亮。
4. 再问一个库外问题（如“火星大气成分？”）→ **拒答**。
5. 指出 hash 嵌入提示：只验证流水线，不宣称语义效果。

### 2.6 真实/演示研究（30 秒）

1. 研究任务页提交“比较高光谱动态图与 HybridSN”。
2. 展示 queued → running → completed、事件时间线、Trace ID。
3. 报告头显示“演示模式、不是调研结果”。
4. 说明真实 GPT Researcher 本地 PDF 模式已用 DeepSeek 完成 10/10 任务；网页模式完成 10/10 Tavily 任务，代理环境需临时放行。

## 3. 演示时必须主动说明的边界

- GPT Researcher 是上游 Apache-2.0 引擎，搜索/抓取/报告生成不是本人原创；
- Demo 不是真实调研；
- hash 不是语义模型；
- 原文匹配 ≠ 事实正确 ≠ 实验可比；
- 合成夹具 100% 只证明流水线；
- Docker 未验证；本地 PDF 10/10、Tavily 网页 10/10、3 篇真实论文抽取均已完成（网页依赖代理放行；指标绑定仍是缺口）。

## 4. 当前环境未完成的可视化

Windows 沙箱禁止 Chrome 的 Mojo 命名管道，headless 截图失败。README 中的界面图是**结构示意**，不是运行截图。若你在普通桌面环境运行，可用：

```powershell
chrome --headless=new --window-size=1440,1600 --screenshot=ui.png http://127.0.0.1:8000/
```

这不会影响功能演示；真实浏览器打开页面即可。
