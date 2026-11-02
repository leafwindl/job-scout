"""CDP 逐层排查：连接、建页、导航，每步都打印。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

from job_scout.tools.cdp import cdp_endpoint, is_cdp_alive

print("alive:", is_cdp_alive(9222))

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp(cdp_endpoint(9222))
print("browser:", b.version)
print("contexts:", len(b.contexts))
ctx = b.contexts[0]
print("pages in ctx:", len(ctx.pages))
for p in ctx.pages:
    print("   existing page:", p.url)

p = ctx.new_page()
print("new page url (before):", p.url)

p.goto("https://example.com", wait_until="domcontentloaded", timeout=30_000)
print("new page url (after example.com):", p.url)
print("title:", p.title())
print("html_len:", len(p.content()))

try:
    p.goto("https://www.zhipin.com/", wait_until="domcontentloaded", timeout=30_000)
    print("after zhipin url:", p.url)
    p.wait_for_timeout(5000)
    print("zhipin title:", p.title())
    print("zhipin html_len:", len(p.content()))
    print("zhipin body:", p.inner_text("body")[:120].replace("\n", " "))
except Exception as e:
    print("zhipin goto failed:", e)

p.close()
pw.stop()
