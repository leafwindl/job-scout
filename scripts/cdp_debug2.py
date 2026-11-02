"""深度排查：监听导航过程中的请求/失败/崩溃事件。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

URL = "https://www.zhipin.com/web/geek/jobs?query=Agent&city=101280100"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]
p = ctx.new_page()

p.on("crash", lambda: print("!! CRASH"))
p.on("requestfailed", lambda r: print("FAILED", r.url[:90], r.failure))
p.on(
    "response",
    lambda r: print("RESP", r.status, r.url[:90])
    if "zhipin" in r.url and ("document" in r.request.resource_type or "xhr" in r.request.resource_type)
    else None,
)

print("before:", p.url)
try:
    resp = p.goto(URL, wait_until="domcontentloaded", timeout=30_000)
    print("goto resp:", resp.status if resp else None, resp.url[:90] if resp else "")
except Exception as e:
    print("goto raised:", type(e).__name__, str(e)[:200])

p.wait_for_timeout(4000)
print("after url:", p.url)
try:
    print("readyState:", p.evaluate("document.readyState"))
    print("location  :", p.evaluate("document.location.href"))
    print("html_len  :", len(p.content()))
    print("body_len  :", len(p.inner_text("body")))
except Exception as e:
    print("eval failed:", type(e).__name__, str(e)[:200])

p.close()
pw.stop()
