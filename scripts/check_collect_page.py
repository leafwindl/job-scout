"""验证 /collect 页。只读页面，不点「开始采集」（避免真的打开 BOSS）。"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

URL = "http://localhost:3000/collect"


def main() -> None:
    with sync_playwright() as p:
        browser = None
        for channel in ("msedge", "chrome", None):
            try:
                browser = p.chromium.launch(channel=channel) if channel else p.chromium.launch()
                break
            except Exception as e:  # noqa: BLE001
                print(f"启动 {channel or 'default'} 失败: {str(e)[:60]}")
        if browser is None:
            sys.exit("没有可用浏览器")

        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(2500)

        checks = {
            "标题「采集」": page.locator("h1", has_text="采集").count() > 0,
            "开始采集按钮": page.get_by_role("button", name="开始采集").count() > 0,
            "重置状态按钮": page.get_by_role("button", name="重置状态").count() > 0,
            "关键词输入框": page.locator('input[placeholder="Agent 实习"]').count() > 0,
            "库内岗位数字": page.locator("text=库内岗位").count() > 0,
        }

        body = page.inner_text("body")
        checks["显示 456 条"] = "456" in body
        checks["状态已完成/采集中"] = ("已完成" in body) or ("采集中" in body)

        print("=== /collect 页面检查 ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")

        page.screenshot(path="data/collect_page.png", full_page=True)
        print("\n截图: data/collect_page.png")
        browser.close()

        if not all(checks.values()):
            sys.exit(1)


if __name__ == "__main__":
    main()
