"""截图验证 P2 公司画像 + P3 技术准备页。"""

from __future__ import annotations

import sys
import urllib.parse

from playwright.sync_api import sync_playwright


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

        page = browser.new_page(viewport={"width": 1280, "height": 1100})

        # P3 技术准备
        page.goto("http://localhost:3000/prep", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("text=建议优先补", timeout=120000)
        page.wait_for_timeout(1500)
        body = page.inner_text("body")
        checks = {
            "技术准备标题": "技术准备" in body,
            "概览": "缺口" in body or "可迁移" in body or "优先" in body,
            "建议优先补": "建议优先补" in body,
            "可放大": "没讲清楚" in body,
            "可跳过": "不值得花时间" in body,
            "高频要求": "高频要求" in body,
        }
        print("=== /prep ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")
        page.screenshot(path="data/check_prep.png", full_page=True)

        # P2 公司画像
        name = urllib.parse.quote("安点科技")
        page.goto(f"http://localhost:3000/company/{name}", wait_until="networkidle", timeout=90000)
        page.wait_for_selector("text=行为信号", timeout=120000)
        page.wait_for_timeout(1500)
        body2 = page.inner_text("body")
        checks2 = {
            "公司名": "安点科技" in body2,
            "在做什么": "在做什么" in body2,
            "技术风格": "技术风格" in body2,
            "什么人吃香": "吃香" in body2,
            "面试可能问": "面试大概会问" in body2,
            "行为信号": "行为信号" in body2,
        }
        print("\n=== /company ===")
        for k, v in checks2.items():
            print(f"  {k}: {v}")
        page.screenshot(path="data/check_company.png", full_page=True)

        browser.close()
        if not all(list(checks.values()) + list(checks2.values())):
            sys.exit(1)


if __name__ == "__main__":
    main()
