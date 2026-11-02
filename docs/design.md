# 设计说明

## 1. 问题拆解

要回答的问题不是「怎么爬 BOSS」，而是：

> **市面上招 Agent 的岗位，到底在要什么？我简历该突出什么？**

所以整条链路的终点是**决策**，不是**数据**。数据只是中间产物。

由此推出三个必须有的能力：

1. **采集** —— 拿到岗位列表 + JD 全文
2. **抽取** —— 把非结构化 JD 变成结构化字段（技能、经验、薪资）
3. **统计** —— 把字段变成结论（哪些技能出现频率最高、薪资带在哪）

## 2. 为什么是「人在环」而不是全自动

BOSS直聘有登录态、验证码、行为风控。全自动意味着：

- 要绕过验证码 → 越界
- 要高频请求 → 封号，且对站点不友好
- 要存账号密码 → 安全风险

「人在环」方案：**用户手动扫码登录，Agent 只读取浏览器里用户已加载的页面**。

这带来三个好处，正好都是工程亮点：

- **合规**：不破解、不高频、不越权
- **技术上刚好落在 LangGraph 的强项**：`interrupt` 暂停等人、`checkpoint` 保存现场、恢复后继续
- **面试可讲**：长任务中断恢复，是真实痛点

## 3. LangGraph 状态设计

```python
class ScoutState(TypedDict):
    query: SearchQuery
    page: int
    listings: Annotated[list[JobPosting], add]   # 累加
    postings: Annotated[list[JobPosting], add]
    errors: Annotated[list[str], add]
    report_path: str | None
```

关键点：

- `Annotated[..., add]` 让并行分支的结果能合并，不用自己写 reducer
- 采集循环用 `page` + 条件边实现，不写 `while`
- `await_login` 里 `interrupt()`，checkpoint 存 SQLite，进程挂了也能续

## 4. 节点职责

| 节点 | 做什么 | 失败怎么办 |
|---|---|---|
| `plan_search` | 关键词/城市 → URL 列表 | 参数校验失败直接报错退出 |
| `await_login` | `interrupt()` 等人登录 | 超时上限，超时终止 |
| `collect_list` | 逐页读取，落 `listings` | 单页失败记 `errors`，继续下一页 |
| `fetch_detail` | 打开详情补 JD | 失败保留浅字段，标记 `partial` |
| `extract` | LLM 抽取 → `JobPosting` | 校验失败重试 1 次，再失败降级为规则解析 |
| `dedupe_store` | 按 `(source, job_id)` 去重入库 | 单条失败跳过并计数 |
| `analyze` | 统计技能/薪资/经验 | 样本不足时报告标注「样本 < N，仅供参考」 |
| `report` | 生成 Markdown | —— |

## 5. 和三个学习项目的关系

| 项目 | 借鉴什么 |
|---|---|
| LangGraph | `StateGraph`、条件边、`interrupt`、checkpoint、子图 |
| deer-flow | 长任务的限速与断点续跑；失败不中断整体；结构化事件流 |
| Dify | `SourceAdapter` 的统一节点接口；「变量池」式的字段传递 |

## 6. 评测怎么做

这是本项目能不能写进简历的分水岭。

- 构造 **30–50 条**人工标注的 JD（标题、技能、经验、薪资区间）
- 指标：
  - **抽取准确率**：字段级 F1（技能集合用集合 F1）
  - **端到端成功率**：一次采集任务完整跑通的比例
  - **成本**：单条 JD 的 token 消耗
- 回归：改 prompt / 换模型后重跑，对比三项指标

没有这组数字，项目就只是 demo。

## 7. 里程碑

- [ ] M1：Playwright 打开 BOSS，人工登录后能稳定拿到第一页 HTML
- [ ] M2：解析出 10 条 `JobPosting`，入库
- [ ] M3：接入 LangGraph，`interrupt` + checkpoint 跑通
- [ ] M4：LLM 抽取 JD 全文，字段准确率 > 80%
- [ ] M5：统计报告 + 简历建议
- [ ] M6：评测集 + 指标基线
