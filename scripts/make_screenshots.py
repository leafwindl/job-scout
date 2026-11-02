"""生成 README 用的截图（存到 docs/screenshots/）。"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

SHOTS = [
    ("/", "home", 0),
    ("/jobs", "jobs", 1500),
    ("/profile", "profile", 2000),
    ("/prep", "prep", 0),  # 慢慢等，LLM 分析
    ("/ask", "ask", 800),
]


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

        page = browser.new_page(viewport={"width": 1360, "height": 900})

        for path, name, wait in SHOTS:
            url = f"http://localhost:3000{path}"
            page.goto(url, wait_until="networkidle", timeout=120000)
            if wait:
                page.wait_for_timeout(wait)
            else:
                page.wait_for_timeout(4000)
            dest = OUT / f"{name}.png"
            page.screenshot(path=str(dest), full_page=False)
            print(f"  {name}.png  <- {path}")

        # 公司画像单截
        name = urllib.parse.quote("安点科技")
        page.goto(f"http://localhost:3000/company/{name}", wait_until="networkidle", timeout=120000)
        page.wait_for_selector("text=行为信号", timeout=120000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "company.png"), full_page=False)
        print("  company.png  <- /company/安点科技")

        browser.close()


if __name__ == "__main__":
    main()
