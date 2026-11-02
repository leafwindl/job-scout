"""看这个标签页是不是在不停重载：轮询 URL，并截图。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

page = next((p for p in ctx.pages if "zhipin.com/web/geek/jobs" in p.url), None)
if page is None:
    print("没有职位搜索页")
    pw.stop()
    raise SystemExit(0)

for i in range(8):
    try:
        u = page.url
    except Exception as e:
        u = f"<url err {type(e).__name__}>"
    try:
        title = page.title()
    except Exception as e:
        title = f"<title err {type(e).__name__}>"
    print(f"{i:>2}  {u[:90]}  | {str(title)[:30]}")
    page.wait_for_timeout(1200)

try:
    page.screenshot(path="data/raw/_loop_state.png")
    print("screenshot -> data/raw/_loop_state.png")
except Exception as e:
    print("截图失败:", type(e).__name__, str(e)[:120])

pw.stop()
