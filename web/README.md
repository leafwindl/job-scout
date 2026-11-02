# job-scout web

Next.js 前端，消费 `api/`（FastAPI）的四个接口。

## 启动

```bash
# 1. 后端（在项目根目录）
uv run uvicorn api.app.main:app --reload --port 8001

# 2. 前端（本目录）
pnpm install     # 首次
pnpm dev         # http://localhost:3000
```

> 后端固定 8001：本机 8000 被另一个项目占用。

## 页面

| 路由 | 内容 | 数据来源 |
|---|---|---|
| `/` | 概览：语料规模、生成模式、服务状态 | `/health` |
| `/ask` | 问答：SSE 流式回答 + 引用卡片 | `/ask/stream` |
| `/jobs` | 岗位列表：关键词 + 方向筛选 + 分页 | `/jobs` |
| `/jobs/[id]` | 岗位详情：JD 全文 | `/jobs/{id}` |
| `/dashboard` | 数据看板：iframe 嵌入静态图表 | `/dashboard.html` |
| `/eval` | 评测报告：指标表 + 结论 | 静态数据 |

## 看板文件

`public/dashboard.html` 由 `scripts/sync-dashboard.mjs` 从 `../data/dashboard.html` 复制，
`pnpm dev` / `pnpm build` 前会自动执行。

重新生成看板后刷新页面即可。

## 环境变量

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8001   # 默认值，一般不用改
```

## 已知限制

- 无 LLM Key 时问答走抽取式模式，页面会显示「（未接入生成模型…）」
- SSE 依赖浏览器的 EventSource，不支持自定义 header
