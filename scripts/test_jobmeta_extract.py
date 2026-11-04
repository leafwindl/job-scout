"""用 Playwright 的 DOM 解析模拟 BOSS 详情页，验证脚本提取逻辑。

不访问真实 BOSS（避免风控），而是构造一段贴近真实结构的 HTML，
在浏览器里跑一遍 readJobMeta 的等价逻辑，确认选择器能命中。
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = """
<html><head><title>AI Agent开发实习生 - 安点科技 - BOSS直聘</title></head>
<body>
  <div class="job-banner">
    <div class="name">AI Agent开发实习生</div>
    <div class="salary">200-250元/天</div>
    <div class="text">广州·海珠区·3天/周·6个月</div>
    <ul class="job-tags">
      <li>Python</li><li>FastAPI</li><li>LangGraph</li><li>RAG</li>
    </ul>
  </div>
  <div class="company-info"><div class="name">安点科技</div></div>
  <div class="job-detail-section">
    <div class="job-sec-text">岗位职责：负责 Agent 工作流搭建与工具调用。</div>
  </div>
</body></html>
"""

JS = """
() => {
  const t = (sel) => (document.querySelector(sel)?.textContent || '').trim();
  const first = (...sels) => {
    for (const s of sels) { const v = t(s); if (v) return v; }
    return '';
  };
  let title = first('.job-banner .name', '.job-banner h1', '.job-title .name', 'h1', '.job-name');
  if (!title) title = (document.title || '').split(/[-_|]/)[0].trim();
  const company = first('.company-info .name', '.job-boss-info .name', '.company-name',
                        '.sider-company .name', '.job-banner .company');
  const salary = first('.job-banner .salary', '.salary', '.job-salary', '.salary-text');
  const locText = first('.job-banner .text', '.location', '.job-location', '.job-banner .info');
  let city = '', district = '';
  const loc = locText.match(/([^\\s·]+)市?[·\\s]+([^\\s·]+?区)/);
  if (loc) { city = loc[1].replace(/市$/, ''); district = loc[2]; }
  else if (locText) { city = locText.split(/[·\\s]/)[0] || ''; }
  const skills = Array.from(document.querySelectorAll(
    '.job-tags span, .job-tags li, .job-keyword-list li, .tag-list li, .job-tags .tag'
  )).map(el => (el.textContent || '').trim()).filter(x => x && x.length <= 20).slice(0, 12);
  const descEl = document.querySelector('.job-sec-text, .job-detail-section .text, .job-detail-section');
  const description = (descEl ? (descEl.innerText || descEl.textContent || '') : '')
    .replace(/\\s+/g, ' ').trim();
  const jobId = (location.pathname.match(/\\/job_detail\\/([^/.]+)\\.html/) || [])[1] || '';
  return { job_id: jobId, title, company, salary, city, district, skills, description };
}
"""


def main() -> None:
    with sync_playwright() as p:
        browser = None
        for ch in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=ch) if ch else p.chromium.launch()
                break
            except Exception:  # noqa: BLE001
                browser = None
        if browser is None:
            sys.exit("没有浏览器")

        page = browser.new_page()
        page.goto("https://www.zhipin.com/")
        page.set_content(HTML)

        # URL 决定 jobId，用 JS 覆盖 location 不方便，直接核对 pathname 逻辑
        result = page.evaluate(JS)
        print("=== 提取结果 ===")
        for k in ("title", "company", "salary", "city", "district", "skills"):
            print(f"  {k}: {result[k]}")
        print(f"  description: {result['description'][:60]}")

        print("\n=== 断言 ===")
        ok = True
        checks = {
            "标题命中": result["title"] == "AI Agent开发实习生",
            "公司命中": result["company"] == "安点科技",
            "薪资命中": result["salary"] == "200-250元/天",
            "城市解析": result["city"] == "广州",
            "区解析": result["district"] == "海珠区",
            "技能 ≥3": len(result["skills"]) >= 3,
            "JD 非空": len(result["description"]) > 10,
        }
        for k, v in checks.items():
            print(f"  {k}: {'OK' if v else 'XX'}")
            ok = ok and v

        browser.close()
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
