"""检查 /collect 页的新「采集设置」卡片。"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
OUT.mkdir(parents=True, exist_ok=True)


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

        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto("http://localhost:3000/collect", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2500)

        body = page.inner_text("body")
        print("=== 文案检查 ===")
        for kw in ("采集设置", "只收实习岗", "只要 AI / Agent 相关", "抓到就推送",
                   "无新增自动停", "目标条数", "采集开关在网页"):
            print(f"  「{kw}」: {kw in body}")

        print("\n=== 复选框 ===")
        boxes = page.locator("input[type=checkbox]")
        print(f"  数量: {boxes.count()}")
        for i in range(boxes.count()):
            checked = boxes.nth(i).is_checked()
            print(f"    #{i+1} checked={checked}")

        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "collect-settings.png"), full_page=False)
        print("\n  已截图 data/ui-check/collect-settings.png")

        browser.close()


if __name__ == "__main__":
    main()
