"""生成一份模拟简历 PDF，用来测解析链路（不需要真实简历）。"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = """
<html><head><meta charset="utf-8"><style>
body { font-family: "Microsoft YaHei", sans-serif; padding: 40px; font-size: 14px; line-height: 1.7; }
h1 { font-size: 24px; margin: 0 0 4px; }
h2 { font-size: 16px; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 20px; }
.skills span { display: inline-block; border: 1px solid #999; border-radius: 4px; padding: 1px 8px; margin: 2px; }
</style></head><body>
<h1>林小满</h1>
<p>求职意向：AI 应用开发实习生｜广州｜每周 5 天，可实习 6 个月</p>

<h2>教育背景</h2>
<p>广州大学 · 计算机科学与技术 · 本科 · 2024.09 - 2028.06</p>
<p>GPA 3.6/4.0，专业前 15%</p>

<h2>技能</h2>
<div class="skills">
  <span>Python</span><span>FastAPI</span><span>LangChain</span><span>LangGraph</span>
  <span>RAG</span><span>MySQL</span><span>Redis</span><span>Docker</span>
  <span>Git</span><span>Prompt Engineering</span>
</div>

<h2>项目经历</h2>
<p><strong>岗位情报 RAG 系统</strong>（个人项目）2026.09 - 2026.11</p>
<ul>
  <li>用浏览器脚本采集 453 条真实招聘 JD，构建结构化语料库</li>
  <li>设计「一条 JD 一个 chunk」策略，A/B 实验使 MRR 从 0.723 提升到 0.864</li>
  <li>实现 BM25 + 向量双路召回与 RRF 融合，MRR 进一步提升到 0.938</li>
  <li>用 FastAPI + Next.js 做前后端，SSE 流式问答，Docker 一键部署</li>
</ul>

<p><strong>校园二手交易平台</strong>（课程项目）2026.03 - 2026.06</p>
<ul>
  <li>后端用 FastAPI + MySQL，实现商品发布、搜索、订单流程</li>
  <li>用 Redis 缓存热门商品列表，接口 P95 从 180ms 降到 45ms</li>
</ul>

<h2>实习经历</h2>
<p><strong>某创业公司</strong> · 后端开发实习生 · 2025.07 - 2025.09</p>
<ul>
  <li>参与内部管理后台开发，用 Python 写数据同步脚本</li>
  <li>优化慢查询，把报表接口耗时从 3s 降到 800ms</li>
</ul>

<h2>其他</h2>
<p>英语 CET-6 560｜有 GitHub 开源项目 2 个｜熟悉 Linux 常用命令</p>
</body></html>
"""

out = Path("data/resume/_test_resume.pdf")
out.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = None
    for ch in ("msedge", "chrome", None):
        try:
            browser = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
            break
        except Exception:
            browser = None
    page = browser.new_page()
    page.set_content(HTML, wait_until="load")
    page.pdf(path=str(out), format="A4", print_background=True)
    browser.close()

print(f"生成: {out}  ({out.stat().st_size} bytes)")
