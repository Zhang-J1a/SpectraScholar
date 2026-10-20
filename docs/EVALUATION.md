# 评测记录

> 评测日期：2026-10-20 · 环境：Windows 11 / Python 3.12.8 / 单机
> 原则：只记录实际运行结果；未运行的指标写“未验证”。

## 1. 结论先行

| 指标 | 结果 | 数据来源 | 能否用于简历 |
|---|---|---|---|
| 自动化测试 | **66 passed** | `pytest -q` | ✅ 可以 |
| 代码覆盖率 | **87%**（3488 stmts / 465 miss） | `pytest --cov` | ✅ 可以 |
| Lint | **All checks passed** | `ruff check` | ✅ 可以 |
| 合成夹具抽取字段命中 | **20/20** | `scripts/evaluate_pipeline.py` | ✅ 可写“合成夹具” |
| 合成夹具原文证据接受 | **23/23** | 同上 | ✅ 可写“合成夹具” |
| 表格夹具方法级指标 | **6 条 table 指标 + 1 个数据集** | `tests/test_tables.py` | ✅ 可写“表格结构解析” |
| BM25 / 向量 / 混合 Recall@1 | **1.0 / 1.0 / 1.0** | 同上，hash 嵌入 | ⚠️ 三者并列，不能宣称混合提升 |
| BM25 / 向量 / 混合 MRR | **1.0 / 1.0 / 1.0** | 同上 | ⚠️ 同上 |
| 合成夹具引用有效率 | **4/4** | 同上 | ✅ 可写“合成夹具” |
| 工作流完成 | **7/7 节点** | 同上 | ✅ 可以 |
| 真实 GPT Researcher 任务成功率 | **未验证** | 无 Key/外网 | ❌ 不能写 |
| 真实论文字段正确率 | **未验证** | PDF 未下载 | ❌ 不能写 |
| 真实语义 Recall@K | **未验证** | 未用真实 embedding | ❌ 不能写 |
| Token / API 成本 | **未验证** | 未调用真实 API | ❌ 不能写 |
| Docker 构建 | **未验证** | 无 Docker CLI | ❌ 不能写 |

---

## 2. 测试环境与方法

```powershell
cd SpectraScholar-Starter
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt   # 或 uv
.\.venv\Scripts\python.exe -m pytest -q
```

测试使用：

- 独立的 `.test-workspace`（Git 忽略），每个用例前重建；
- 标准库生成的**真实可解析 PDF**（非 mock 字节），包括普通文本页和带线表格页；
- 假 `gpt_researcher` 模块，记录构造参数与调用；
- 假 `AsyncOpenAI`，返回可控 JSON/错误；
- `TestClient` 启动真实 FastAPI 生命周期。

覆盖的验收要求：

1. 正常 API 请求（研究/上传/对比/索引/问答/工作流）。
2. 非法参数（主题过短、重复文档、非法 source、top_k 越界）。
3. 无效 PDF（扩展名、文件头、空文件、超大、加密/损坏路径）。
4. 空文档 / 无检索结果（拒答）。
5. LLM API 超时/失败（Mock：空报告、超时、缺 Key、非法 JSON）。
6. 非法结构化输出（非 JSON、字段类型错误、缺失 page/quote）。
7. 无效页码/虚构引用（page_missing、quote_not_found、value mismatch）。
8. 重复文献与条件不一致（SHA 去重、duplicate IDs、train_ratio 缺失）。
9. 任务状态转换（queued→running→completed/failed；重试；事件）。
10. Demo 与真实模式隔离（`is_demo`、报告头、缺 Key 失败）。
11. 表格解析（表头识别、单一数值、`98.4/97.1` 拒绝、无页文本拒绝、无表格降级、开关关闭）。
12. 表格指标与正文指标合并、方法级来源、可比性表格展示。

---

## 3. 覆盖率

```text
Name                                     Stmts   Miss  Cover
------------------------------------------------------------
spectrascholar\api\comparison.py            65     12    82%
spectrascholar\api\documents.py            110     17    85%
spectrascholar\api\knowledge.py             36      5    86%
spectrascholar\api\research.py              64     10    84%
spectrascholar\api\system.py                32      4    88%
spectrascholar\api\workflows.py             45      4    91%
spectrascholar\citations.py                106      5    95%
spectrascholar\compare.py                  263     23    91%
spectrascholar\evidence.py                 102     27    74%
spectrascholar\extraction\heuristic.py     253     27    89%
spectrascholar\extraction\llm.py           214     44    79%
spectrascholar\extraction\service.py        50      2    96%
spectrascholar\extraction\tables.py        235     47    80%
spectrascholar\main.py                      91      6    93%
spectrascholar\rag\bm25.py                  50      5    90%
spectrascholar\rag\chunking.py              62     14    77%
spectrascholar\rag\embeddings.py            85     27    68%
spectrascholar\rag\index.py                204     38    81%
spectrascholar\rag\service.py              193     51    74%
spectrascholar\research.py                 213     35    84%
spectrascholar\schemas.py                  385      2    99%
spectrascholar\settings.py                 106      5    95%
spectrascholar\store.py                    219     22    90%
spectrascholar\workflow.py                 214     36    83%
------------------------------------------------------------
TOTAL                                     3488    465    87%
```

未覆盖部分主要是：真实 provider 客户端、PDF 加密/损坏、部分索引持久化分支、表格解析的异常分支。

---

## 4. 合成夹具评测（不是真实论文结论）

### 4.1 数据

`scripts/evaluate_pipeline.py` 生成三份合成 PDF：

- `dynamic_gnn.pdf`：GCN + KNN + dynamic graph；Indian Pines；10% 训练；9x9；random split；OA 98.4%、Kappa 0.977。
- `hybridsn.pdf`：HybridSN + 3D/2D-CNN；Indian Pines；10%；9x9；random split；OA 97.1%、AA 96.5%；RBF/static baseline。
- `table_paper.pdf`：一张**带实际线条**的表格，表头 `Method / OA / AA / Kappa`，两行 HybridSN、GCN；标题包含 Indian Pines、10%、9x9、random split。

这些是**人工构造的夹具**，不是 HybridSN/SSRN 原论文。

### 4.2 实际输出

```text
Corpus: synthetic_fixture / real_papers=False
Embedding: hash-512
Extraction field accuracy: 20/20 (1.0)
Evidence acceptance: 23/23 (1.0)
Retrieval [bm25]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [vector]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Retrieval [hybrid]: Recall@1=1.0 Recall@3=1.0 MRR=1.0 median=2ms
Citation validity: 1.0 (4 checks)
Workflow: completed 7/7 steps
Latency: {'compare': 123, 'index': 18, 'search_median': 3, 'answer': 20, 'workflow': 379}
```

完整 JSON：[`evaluation_results.json`](evaluation_results.json)。

### 4.3 指标定义

| 指标 | 定义 |
|---|---|
| 字段命中 | 每篇论文检查 title/methods/datasets/metrics/graph/train_ratio/patch_size；表格论文不检查标题，共 20 项 |
| 证据接受 | `verified_quote` 证据数 / 证据总数 |
| Recall@K | 标注的 (filename, page) 是否出现在 Top-K 命中 |
| MRR | 首次命中的排名倒数均值 |
| 引用有效率 | 回答中非失败引用数 / 总引用检查数 |

### 4.4 检索消融的真实结论

三种模式在合成夹具上并列 1.0，原因很明确：

- 只有 3 篇文档、约 8 个 chunk，查询词与标注页高度重合；
- `EMBEDDING_BACKEND=hash` 是**词法哈希**，不是语义模型；它和 BM25 都依赖词面重合；
- 因此这组数字**不能**证明“混合检索优于 BM25”或“向量检索有语义泛化”。
- 要得到有意义的 ablation，必须使用真实 embedding（OpenAI/sentence-transformers）和真实论文/更难查询；见第 6 节计划。

### 4.5 表格解析的实际验证

- `pdfplumber` 从带线表格中识别出 4 列、3 行（含表头）；
- 生成 6 条 `source=table` 指标，方法列分别为 `HybridSN` / `GCN`；
- 每条指标都有页文本中的数值证据，`verified_quote`；
- 数据集 `Indian Pines` 从表格标题上下文提取并核验；
- 训练比例 10%、补丁 9x9、协议 random split 从标题上下文提取；
- `98.4/97.1` 这类多值单元格被记录为 `ambiguous_table_cell`，不猜测；
- 表格数值不在页文本时记录 `quote_not_found`；
- 无表格/开关关闭/PDF 无法打开时自动降级并写 note，不使整个抽取失败。

### 4.6 不能从这组数字推出的结论

- 不能推出真实论文上的抽取准确率；
- 不能推出 hash 嵌入的语义检索质量；
- 不能推出混合检索相对 BM25 的提升；
- 不能推出 GPT Researcher 的真实任务成功率；
- 不能推出 token 成本；
- 不能推出系统对复杂跨页表、多级表头、公式、扫描件的鲁棒性。

---

## 5. HTTP 端到端冒烟

真实 Uvicorn + `httpx`：

| 步骤 | 结果 |
|---|---|
| `GET /` | 200，约 50 KB |
| 上传 dynamic_gnn.pdf | 201 |
| 上传 hybridsn.pdf | 201 |
| Demo 研究 | 202 → completed，报告 623 字符 |
| 对比 | 200，OA 98.4% / 97.1% 可比，1/2 名；Kappa 单篇不可比 |
| 索引 | 200，4 chunks |
| 检索 | 200，首位命中 dynamic_gnn p.1 |
| 问答 | 200，grounded=true，refusal=false，引用通过 |
| 工作流 | 202 → completed，7/7 节点，报告 11,795 字符 |
| 报告/对比下载 | 200 |
| OpenAPI | 200 |

表格 PDF 的 API 对比在 `tests/test_tables.py` 中验证：返回 `source=table`、`method=HybridSN/GCN`，Markdown 指标表包含“来源”列。

控制台中文出现的乱码是 PowerShell 编码显示问题；已用 `repr`/`ord` 验证 API 返回的是正确 Unicode（如 `0x672c 0x62a5 0x544a`）。

---

## 6. 真实论文评测计划（未执行）

清单：[`../eval/papers.manifest.json`](../eval/papers.manifest.json)

- HybridSN：DOI 10.1109/LGRS.2019.2918719
- SSRN：DOI 10.1109/TGRS.2017.2755542
- GCN-HSI：DOI 10.1109/TGRS.2020.3015157 / arXiv 2008.02457

执行条件：

1. 通过机构订阅或开放获取合法下载 PDF；
2. 两人独立标注 10～20 个字段，分歧由第三人裁决；
3. 记录：
   - 字段 Precision/Recall/F1；
   - 表格/正文指标来源准确率；
   - 引用有效率（verified / total）；
   - Recall@1/3/5、MRR；
   - 单任务耗时、失败率；
   - 真实 API token 与费用；
4. 分别运行 heuristic、LLM、hash、OpenAI embedding 的 ablation；
5. 把失败案例写入 `docs/DEVELOPMENT_LOG.md`，不要只报平均值。

在完成前，README 和简历中只能写“合成夹具验证”，不能写真实论文准确率。

---

## 7. 复现命令

```powershell
# 单元/接口测试
.\.venv\Scripts\python.exe -m pytest -q

# Lint
.\.venv\Scripts\ruff.exe check spectrascholar tests scripts

# 覆盖率
.\.venv\Scripts\python.exe -m pytest --cov=spectrascholar --cov-report=term

# 合成夹具评测（写入 docs/evaluation_results.json，含三模式消融）
.\.venv\Scripts\python.exe scripts\evaluate_pipeline.py

# 真实 GPT Researcher 检查（需要 live 依赖）
.\.venv\Scripts\python.exe scripts\check_gptr_api.py

# 真实 API 冒烟（需要 Key/网络；失败会非零退出）
.\.venv\Scripts\python.exe scripts\smoke_gptr.py --topic "..." --source web
```
