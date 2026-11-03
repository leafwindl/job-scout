"""验证「抓取这条 JD」按钮出现在无 JD 的岗位页上。"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
OUT.mkdir(parents=True, exist_ok=True)


def find_nojd() -> str | None:
    with urllib.request.urlopen("http://127.0.0.1:8001/jobs?size=60", timeout=20) as r:
        d = json.loads(r.read().decode())
    for x in d["items"]:
        if not x["has_jd"]:
            return x["job_id"]
    return None


def main() -> None:
    jid = find_nojd()
    if not jid:
        print("没有无 JD 的岗位可测")
        return
    print(f"测试岗位: {jid}")

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
        page.goto(f"http://localhost:3000/jobs/{jid}", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(1500)

        body = page.inner_text("body")
        checks = {
            "显示未抓取提示": "还没有抓取到 JD 正文" in body,
            "有「抓取这条 JD」按钮": page.get_by_role("button", name="抓取这条 JD").count() > 0,
            "有采集任务入口": "去采集任务" in body,
        }
        print("=== /jobs/[id] 无 JD 状态 ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")

        page.screenshot(path=str(OUT / "grabjd.png"), full_page=False)

        # 点一下按钮，确认进入 waiting 态（不真的打开新标签会失败，但状态要变）
        btn = page.get_by_role("button", name="抓取这条 JD")
        if btn.count() > 0:
            try:
                btn.first.click()
                page.wait_for_timeout(1500)
                body2 = page.inner_text("body")
                print(f"  点击后进入等待态: {'等脚本回传正文' in body2}")
            except Exception as e:  # noqa: BLE001
                print(f"  点击异常（可能弹窗被拦）: {str(e)[:60]}")

        browser.close()


if __name__ == "__main__":
    main()
