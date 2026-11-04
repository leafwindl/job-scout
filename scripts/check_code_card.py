"""检查 /profile 页的「项目代码」卡片是否真的渲染出来。"""

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

        page = browser.new_page(viewport={"width": 1440, "height": 950})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(f"[{m.type}] {m.text}") if m.type == "error" else None)

        page.goto("http://localhost:3000/profile", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2500)

        body = page.inner_text("body")
        print("=== 文案检查 ===")
        for kw in ("项目代码", "扫描并关联", "项目路径", "还没有提交项目代码"):
            print(f"  「{kw}」: {kw in body}")

        # 找卡片
        print("\n=== DOM 检查 ===")
        count = page.locator("text=项目代码").count()
        print(f"  「项目代码」文本节点: {count} 个")
        print(f"  输入框数量: {page.locator('input.input').count()}")

        # 滚到底截图
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "profile-bottom.png"), full_page=False)
        print("\n  已截图 data/ui-check/profile-bottom.png")

        if errors:
            print("\n=== 页面错误 ===")
            for e in errors[:5]:
                print(f"  {e[:160]}")

        browser.close()


if __name__ == "__main__":
    main()
