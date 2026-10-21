# 真实研究任务评测（本地 PDF）

- 生成时间：2026-10-21T05:17:13+00:00
- 后端：`gptr` / `deepseek:deepseek-chat`
- 语料：`synthetic_fixture`（不是真实论文）
- 任务数：10；完成：10；失败：0；成功率：1.0
- 延迟：p50=23993ms，p95=33529ms
- 报告平均字符：14742.5
- 上游 costs 元数据合计：0.663485
- 引用审计合计：{'total': 301, 'verified_local': 0, 'page_only_local': 0, 'failed_local': 0, 'external_unchecked': 46, 'local_file_unverified': 255, 'unsupported_claims': 88}

| # | 状态 | 报告字符 | elapsed_ms | page+ | local_file | unsupported | error |
|---|---|---|---|---|---|---|---|
| 1 | completed | 14905 | 33529 | 0 | 6 | 20 |  |
| 2 | completed | 13677 | 21888 | 0 | 29 | 8 |  |
| 3 | completed | 15363 | 23993 | 0 | 15 | 6 |  |
| 4 | completed | 12933 | 20158 | 0 | 25 | 8 |  |
| 5 | completed | 14202 | 21007 | 0 | 34 | 10 |  |
| 6 | completed | 12967 | 27080 | 0 | 0 | 15 |  |
| 7 | completed | 15828 | 25588 | 0 | 0 | 3 |  |
| 8 | completed | 13915 | 24409 | 0 | 24 | 4 |  |
| 9 | completed | 15513 | 23199 | 0 | 44 | 6 |  |
| 10 | completed | 18122 | 26198 | 0 | 78 | 8 |  |

> 这是合成夹具上的任务可靠性评测。真实网页检索与真实论文质量仍未验证。
