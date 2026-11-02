"""验证：直接复用用户已有的标签页导航，是否会正常渲染。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

URL = "https://www.zhipin.com/web/geek/jobs?query=Agent%E5%BC%80%E5%8F%91&city=101280100"
COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

print("现有标签:")
for i, p in enumerate(ctx.pages):
    try:
        print(f"  [{i}] {p.url[:80]}")
    except Exception:
        print(f"  [{i}] <closed>")

page = ctx.pages[0]
print("\n复用 [0] 导航到搜索页…")
page.bring_to_front()
page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
page.wait_for_timeout(6000)

print("url    =", page.url[:90])
print("title  =", page.title()[:40])
print("cards  =", page.evaluate(COUNT))
print("bodyLen=", len(page.inner_text("body")))

page.mouse.click(420, 420)
page.wait_for_timeout(500)
for i in range(6):
    try:
        page.keyboard.press("End")
        page.wait_for_timeout(2000)
        print(f"  End #{i + 1}: scrollY={page.evaluate('window.scrollY')} cards={page.evaluate(COUNT)}")
    except Exception as e:
        print(f"  End #{i + 1} 出错:", type(e).__name__, str(e)[:60])

pw.stop()
