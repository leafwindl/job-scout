"""验证 /prep 和 /company 的两阶段加载。

先截「统计已出、AI 还在转」的中间态，再截完成态。
"""

from __future__ import annotations

import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
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

        # ---- /prep ----
        page.goto(f"{BASE}/prep", wait_until="domcontentloaded", timeout=90000)
        # 等统计出现（高频要求区块）
        page.wait_for_selector("text=高频要求", timeout=30000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "prep-loading.png"), full_page=False)
        txt = page.inner_text("body")
        print("=== /prep 中间态 ===")
        print("  统计已渲染:", "高频要求" in txt)
        print("  AI 占位在:", ("正在生成学习计划" in txt) or ("正在" in txt))
        print("  秒数计数:", any(f"{i}s" in txt for i in range(0, 60)))

        # 等 AI 完成
        page.wait_for_selector("text=怎么学", timeout=120000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "prep-done.png"), full_page=False)
        print("  完成态有「怎么学」: True")

        # ---- /company ----
        name = urllib.parse.quote("安点科技")
        page.goto(f"{BASE}/company/{name}", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_selector("text=行为信号", timeout=30000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "company-loading.png"), full_page=False)
        txt2 = page.inner_text("body")
        print("\n=== /company 中间态 ===")
        print("  统计已渲染:", "行为信号" in txt2)
        print("  AI 占位在:", ("正在分析" in txt2))

        page.wait_for_selector("text=在做什么", timeout=120000)
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "company-done.png"), full_page=False)
        print("  完成态有「在做什么」: True")

        browser.close()


if __name__ == "__main__":
    main()
