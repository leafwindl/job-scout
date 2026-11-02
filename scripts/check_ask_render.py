"""用 Playwright 验证问答页的 Markdown 渲染。

只访问本地 localhost，不碰招聘站点。
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

URL = "http://localhost:3000/ask"


def main() -> None:
    with sync_playwright() as p:
        # 用系统 Edge/Chrome，避免下载 Playwright 专用浏览器
        browser = None
        for channel in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception as e:  # noqa: BLE001
                print(f"启动 {channel or 'default'} 失败: {str(e)[:80]}")
        if browser is None:
            sys.exit("没有可用的浏览器")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")

        # 点第一个示例问题
        page.get_by_role("button", name="哪些实习岗要求 LangGraph？").click()

        # 等回答渲染出来
        page.wait_for_selector(".md", timeout=90_000)
        page.wait_for_timeout(6000)

        html = page.inner_html(".md")
        checks = {
            "粗体 <strong>": "<strong>" in html,
            "列表 <ul> 或 <ol>": ("<ul>" in html) or ("<ol>" in html),
            "引用锚点 [1]": 'href="#cite-1"' in html,
            "引用卡片": page.locator(".cite-card").count(),
        }
        print("=== 渲染检查 ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")

        page.screenshot(path="data/ask_render.png", full_page=True)
        print("\n截图: data/ask_render.png")
        browser.close()

        if not all([checks["粗体 <strong>"], checks["列表 <ul> 或 <ol>"], checks["引用锚点 [1]"]]):
            sys.exit(1)


if __name__ == "__main__":
    main()
