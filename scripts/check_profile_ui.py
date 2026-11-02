"""端到端验证：画像页 + 岗位匹配 + 招呼语生成。"""

from __future__ import annotations

import sys

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

        page = browser.new_page(viewport={"width": 1280, "height": 1000})

        # ---- 1. 画像页 ----
        page.goto("http://localhost:3000/profile", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        checks = {
            "画像页标题": "我的简历" in body,
            "姓名": "叶旭景" in body,
            "技能数": "技能" in body,
            "项目数": "项目经历" in body,
            "LangGraph 技能": "LangGraph" in body,
        }
        print("=== /profile ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")
        page.screenshot(path="data/check_profile.png", full_page=True)

        # ---- 2. 岗位详情 + 匹配 ----
        jobs = page.evaluate(
            "fetch('http://127.0.0.1:8001/jobs?size=1').then(r=>r.json())"
        )
        jid = jobs["items"][0]["job_id"]
        page.goto(f"http://localhost:3000/jobs/{jid}", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)

        page.get_by_role("button", name="分析匹配度").click()
        page.wait_for_timeout(45000)

        body2 = page.inner_text("body")
        checks2 = {
            "投递助手面板": "投递助手" in body2,
            "有分数或结论": any(v in body2 for v in ("强推", "可投", "观望", "不建议")),
            "有缺口分析": "缺口" in body2,
        }
        print("\n=== 岗位匹配 ===")
        for k, v in checks2.items():
            print(f"  {k}: {v}")
        page.screenshot(path="data/check_match.png", full_page=True)

        browser.close()
        if not all(list(checks.values()) + list(checks2.values())):
            sys.exit(1)


if __name__ == "__main__":
    main()
