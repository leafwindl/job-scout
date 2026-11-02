"""生成 README 截图（假简历 + 新 UI）。"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

BASE = "http://localhost:3000"


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

        page = browser.new_page(viewport={"width": 1440, "height": 950})

        def shot(path: str, name: str, wait: int = 3000) -> None:
            page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=150000)
            page.wait_for_timeout(wait)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print(f"  {name}.png  <- {path}")

        shot("/", "home")
        shot("/jobs", "jobs")
        shot("/profile", "profile")
        shot("/prep", "prep", 25000)  # LLM 分析要等
        shot("/ask", "ask", 1200)
        shot("/dashboard", "dashboard", 5000)
        shot("/collect", "collect", 3000)

        # 公司画像
        name = urllib.parse.quote("安点科技")
        page.goto(f"{BASE}/company/{name}", wait_until="networkidle", timeout=150000)
        page.wait_for_timeout(25000)
        page.screenshot(path=str(OUT / "company.png"), full_page=False)
        print("  company.png  <- /company/安点科技")

        # 岗位详情 + 匹配（需要点按钮）
        page.goto(f"{BASE}/jobs", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2000)
        # 点第一个岗位
        page.locator("main a[href^='/jobs/']").first.click()
        page.wait_for_timeout(3000)
        # 点「匹配度」tab（新 UI 是三 tab）
        for label in ("匹配度", "分析匹配度"):
            btn = page.get_by_role("button", name=label)
            if btn.count() > 0:
                btn.first.click()
                break
        page.wait_for_timeout(40000)
        page.screenshot(path=str(OUT / "match.png"), full_page=False)
        print("  match.png  <- 岗位详情 + 匹配度")

        browser.close()


if __name__ == "__main__":
    main()
