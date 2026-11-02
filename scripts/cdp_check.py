"""检查 CDP 链路：能否连上浏览器、能否打开页面、能否捕获接口响应。

不写数据库，只做诊断。
    uv run python scripts/cdp_check.py
"""

from __future__ import annotations

from urllib.parse import quote

from job_scout.tools.cdp import CdpCollector, is_cdp_alive

KEYWORD = "Agent开发"
CITY = "101280100"
URL = f"https://www.zhipin.com/web/geek/jobs?query={quote(KEYWORD)}&city={CITY}"


def main() -> None:
    print("cdp alive:", is_cdp_alive(9222))
    col = CdpCollector(port=9222, match="joblist.json")
    try:
        col.open(URL)
        print("url      :", col.url())

        # SPA 首屏先「加载中」，轮询等它稳定
        body = ""
        for i in range(12):
            body = col.body_text()
            if len(body) > 100:
                print("rendered :", f"{i * 2}s")
                break
            if col.captured:
                print("rendered : api captured, body 仍短")
                break
            col.page.wait_for_timeout(2000)

        print("body_len :", len(body))
        print("body_head:", body[:300].replace("\n", " "))

        try:
            shot = col.screenshot("data/raw/_cdp_state.png")
            print("html_len :", len(col.page.content()))
            print("screenshot:", shot.resolve())
        except Exception as e:
            print("截图失败:", e)

        got = col.wait_for_data(timeout_s=10)
        print("captured :", len(col.captured), "(搜索接口响应数)")

        if not got:
            print("\n没捕获到搜索接口。常见原因：")
            print("  1) 未登录 —— 在这个浏览器窗口里登录一次")
            print("  2) 安全验证 —— 手动点按钮过掉")
            print("  3) 不是在职位搜索页")
        else:
            print("\n✓ 链路正常，可以跑 collect 了")
    finally:
        col.close()


if __name__ == "__main__":
    main()
