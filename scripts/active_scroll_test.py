"""验证：把标签置前之后，页面是否正常渲染、滚动是否生效。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

URL = "https://www.zhipin.com/web/geek/jobs?query=Agent%E5%BC%80%E5%8F%91&city=101280100"
COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

for p in list(ctx.pages):
    try:
        if "zhipin.com/web/geek/jobs" in p.url and len(ctx.pages) > 1:
            p.close()
    except Exception:
        pass

page = ctx.new_page()
page.bring_to_front()          # ← 关键：激活标签
page.wait_for_timeout(500)
page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
page.wait_for_timeout(5000)

print("激活后 cards =", page.evaluate(COUNT), " scrollY =", page.evaluate("window.scrollY"))
print("title =", page.title()[:40])

page.mouse.click(420, 420)
page.wait_for_timeout(600)

for i in range(8):
    try:
        page.keyboard.press("End")
        page.wait_for_timeout(2000)
        cards = page.evaluate(COUNT)
        y = page.evaluate("window.scrollY")
        print(f"  End #{i + 1}: scrollY={y:<6} cards={cards}")
    except Exception as e:
        print(f"  End #{i + 1} 出错:", type(e).__name__, str(e)[:70])
        page.wait_for_timeout(2000)

try:
    page.screenshot(path="data/raw/_active_state.png", timeout=10_000)
    print("screenshot ok")
except Exception as e:
    print("截图失败:", type(e).__name__)

pw.stop()
