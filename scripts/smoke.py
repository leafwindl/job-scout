"""冒烟测试：验证浏览器渠道能否打开 BOSS 搜索页。

用法：
    uv run python scripts/smoke.py            # 默认 msedge
    uv run python scripts/smoke.py chrome
    uv run python scripts/smoke.py ""         # 自带 Chromium

无头运行，不会弹窗，只打印诊断信息。
"""

from __future__ import annotations

import sys
from urllib.parse import quote

from playwright.sync_api import sync_playwright

CITY_GUANGZHOU = "101280100"
KEYWORD = "Agent开发"
URL = (
    f"https://www.zhipin.com/web/geek/jobs"
    f"?query={quote(KEYWORD)}&city={CITY_GUANGZHOU}"
)


def main(channel: str | None) -> None:
    print(f"channel = {channel or '(bundled chromium)'}")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=channel, headless=True)
        ctx = browser.new_context(
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.new_page()
        try:
            resp = page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            print("http_status:", resp.status if resp else None)
            print("final_url  :", page.url)
            print("title      :", page.title())

            # SPA 首屏是「加载中，请稍候」，轮询等它真正渲染
            body = ""
            for i in range(15):
                body = page.inner_text("body")
                if len(body) > 100:
                    print("rendered at:", f"{i * 2}s")
                    break
                page.wait_for_timeout(2000)
            else:
                print("rendered at: 超时（30s 仍是加载态）")

            print("body_len   :", len(body))
            print("body_head  :", body[:300].replace("\n", " "))
            print("cards      :", page.locator("li.job-card-wrapper").count())
            print("iframes    :", page.locator("iframe").count())
            print("html_len   :", len(page.content()))
        finally:
            browser.close()


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "msedge"
    main(arg or None)
