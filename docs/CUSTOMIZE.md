# 个人修改导航：从哪个文件开始？

## 先改这四处（新手最友好）

1. `spectrascholar/domains.py`：修改科研领域描述、数据集及报告结构。换成医疗/金融/法律等其他文档场景也可。
2. `spectrascholar/evidence.py`：增加你研究方向独有的字段，例如图节点构造、动态邻接矩阵、主干网络、训练样本占比；并让每个字段必须返回来源。
3. `spectrascholar/schemas.py`：更改论文实体的 Pydantic 数据契约、校验规则和接口响应。
4. `web/index.html`：设计个人品牌、交互页面与研究任务模板；前端外观是辅助，不能替代核心功能。

## 进阶：需要动哪三处？

- `spectrascholar/research.py`：封装 OpenAI/GPT Researcher 的适配器。先不要复制/覆盖 `gpt_researcher/agent.py`。
- `spectrascholar/main.py`：新建业务接口、参数校验、安全和异步流程。
- `spectrascholar/store.py`：把 SQLite 迁移为 PostgreSQL，实现用户会话、知识库管理、任务持久化。

## 推荐个人创新方向

- *HSI SOTA Comparison*：抽取“模型-数据集-样本比例-输入补丁-训练次数-评价指标”组合，只有相同实验设置的数字才能并排排名。
- *Graph Construction Inspector*：抽取 KNN/RBF/动态图构建规则、图节点粒度与图更新频率。
- *Evidence First RAG*：提出引用必须满足“PDF 页码 + 最短原文片段 + 实验上下文”的三重可追溯契约。
- *Failure-aware Research*：做检索 429、LLM 超时、PDF 无法提取、数据库损坏的可靠降级，而不是只演示 happy path。

每做一项功能，都至少有一个自动测试、一个 bad case 和一个简短设计决策说明。别把上游现成能力写成自己的原创。
