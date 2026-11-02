"""渐进滚动测试：一次滚一点，看职位卡片数量会不会增长。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box, .rec-job-list > li').length"
TEXT_HAS = """
(kw) => document.body.innerText.includes(kw)
"""

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

page = next((p for p in ctx.pages if "zhipin.com/web/geek/jobs" in p.url), None)
if page is None:
    print("没找到职位搜索页")
    pw.stop()
    raise SystemExit(0)

print("url:", page.url[:110])
for kw in ("加载更多", "查看更多", "下一页", "没有更多"):
    try:
        print(f"  页面含「{kw}」:", page.evaluate(TEXT_HAS, kw))
    except Exception as e:
        print(f"  检查 {kw} 失败:", type(e).__name__)

start = page.evaluate(COUNT)
print("\n初始卡片数:", start)

for i in range(12):
    try:
        page.mouse.wheel(0, 900)
        page.wait_for_timeout(1200)
        n = page.evaluate(COUNT)
        y = page.evaluate("window.scrollY")
        print(f"  第 {i + 1:>2} 次滚动: scrollY={y:<6} 卡片={n}")
        if n > start + 30:
            break
    except Exception as e:
        print(f"  第 {i + 1} 次出错:", type(e).__name__, str(e)[:80])
        page.wait_for_timeout(1500)

print("最终卡片数:", page.evaluate(COUNT))
pw.stop()
