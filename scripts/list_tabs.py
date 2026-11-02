"""列出所有标签，并给每个截图，看清用户到底看到的是哪一个。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

print("标签数:", len(ctx.pages))
for i, p in enumerate(ctx.pages):
    try:
        url = p.url
    except Exception:
        url = "<closed>"
    try:
        title = p.title()
    except Exception:
        title = "<no title>"
    print(f"\n[{i}] {url[:100]}")
    print(f"     title={title[:50]}")
    if url.startswith("http") and "zhipin" in url:
        try:
            p.bring_to_front()
            p.wait_for_timeout(800)
            path = f"data/raw/_tab_{i}.png"
            p.screenshot(path=path, timeout=8000)
            print(f"     screenshot -> {path}")
        except Exception as e:
            print("     screenshot failed:", type(e).__name__)

pw.stop()
