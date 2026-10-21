# 真实网页研究评测（Tavily）

- 生成时间：2026-10-21T05:56:12+00:00
- 后端：`gptr` / `deepseek:deepseek-chat`
- 检索器：`tavily`
- 任务数：10；完成：10；失败：0；成功率：1.0
- 延迟：p50=36861ms，p95=42714ms
- 报告平均字符：20179.5
- 上游 costs 合计：1.078075
- 来源总数：62
- 引用审计合计：{'total': 443, 'verified_local': 0, 'page_only_local': 0, 'failed_local': 0, 'external_unchecked': 443, 'local_file_unverified': 0, 'unsupported_claims': 31}

| # | 状态 | 报告字符 | elapsed_ms | sources | 外部链接 | 缺引用 | error |
|---|---|---|---|---|---|---|---|
| 1 | completed | 16695 | 42714 | 5 | 39 | 5 |  |
| 2 | completed | 19556 | 36861 | 6 | 35 | 3 |  |
| 3 | completed | 19798 | 38459 | 6 | 44 | 0 |  |
| 4 | completed | 22418 | 37641 | 6 | 63 | 1 |  |
| 5 | completed | 20527 | 35156 | 6 | 53 | 3 |  |
| 6 | completed | 25427 | 37732 | 8 | 55 | 5 |  |
| 7 | completed | 24123 | 42038 | 7 | 47 | 6 |  |
| 8 | completed | 16767 | 30851 | 3 | 36 | 0 |  |
| 9 | completed | 16818 | 35895 | 7 | 31 | 4 |  |
| 10 | completed | 19666 | 35891 | 8 | 40 | 4 |  |

> 这是当前网络代理环境下的真实网页任务评测；外部链接未做内容核验。
> `ALLOW_PRIVATE_URLS=true` 仅用于本地代理环境，会关闭 SSRF 防护，不能用于生产。
