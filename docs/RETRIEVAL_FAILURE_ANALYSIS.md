# 50 题检索失败分析

## 结论

```text
50 题
router Answer-level Recall@5: 78.0%
router Page-level Recall@5:   76.0%
page-level 失败:              12 / 50
```

page-level 失败不是均匀分布，集中在校验成本高的两类：

1. SSRN 的 metadata/首页题；
2. SSRN 的表格页题（p6/p7/p8）。

---

## 失败清单

| 题号 | 文档 | 类别 | gold page | router page rank |
|---|---|---:|---:|---:|
| q011 | ssrn | metadata | 1 | None |
| q012 | ssrn | metadata | 1 | None |
| q013 | ssrn | metadata | 1 | None |
| q037 | ssrn | metadata | 1 | None |
| q038 | ssrn | metadata | 1 | None |
| q014 | ssrn | condition | 6 | 18 |
| q017 | ssrn | metric | 7 | 14 |
| q018 | ssrn | metric | 7 | 13 |
| q019 | ssrn | metric | 7 | 9 |
| q020 | ssrn | metric | 7 | 13 |
| q041 | ssrn | metric | 8 | 18 |
| q024 | cnn_gat | condition | 7 | 7 |

---

## 归因

### 1. SSRN 首页题：缩写与标题不一致

问题里写 `SSRN`，论文首页标题是：

```text
Spectral–Spatial Residual Network for Hyperspectral Image Classification:
A 3-D Deep Learning Framework
```

BM25/hash 不会自动把 `SSRN` 映射到完整标题，因此 5 道首页题 page rank 为 `None`。

这不是排序差，而是**文档别名/缩写没有进入检索**。

### 2. SSRN 表格页题：表格内容跨 chunk

q014/q017-q020/q041 的 gold page 是 6/7/8，属于训练设置与结果表。  
当前按字符切 chunk，表格行/列会被拆开；BM25 能命中文字，但页级排名不稳定。

### 3. q024：只差 2 名

WFCG 的 Indian Pines 条件题 gold page=7，router page rank=7，刚好在 Top-5 外。  
这是阈值问题，不是完全没检索到。

### 4. 中文问题 vs 英文论文

Metadata 和条件题仍存在中文 query → 英文 page 的跨语言问题。  
`nomic-embed-text` 是英文模型，BM25 又不做翻译，所以首页/表格页更容易失败。

---

## 不应当做的事

- 不要为 q011/q012 这类题硬编码 `SSRN` 页面；
- 不要为了 12 道失败题过拟合 router 关键词；
- 不要把 page-level 76% 写成“全部解决”。

---

## 下一步优先级

1. **文档缩写/别名路由**：`SSRN` → 标题/文档；`WFCG`/`HybridSN` 同理；
2. **表格页按行/表头切 chunk**，而不是纯字符切；
3. **页级候选扩展**：对表格页增加候选 chunk，而不是直接改全局排序；
4. 扩到 80–100 题，验证不是 50 题过拟合；
5. 再试多语言 embedding（bge-m3）对照。

当前最准确的结论：

> **page-level 失败集中在校验难度最高的 SSRN 首页/表格页；这是文档别名和表格切分问题，不是简单的“embedding 不够好”。**
