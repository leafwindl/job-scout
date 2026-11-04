"""验证三步解锁流程。"""

from __future__ import annotations

import json
import sqlite3
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
OUT.mkdir(parents=True, exist_ok=True)


def first_job() -> str:
    conn = sqlite3.connect("data/job_scout.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT job_id FROM postings WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
    ).fetchone()
    conn.close()
    return row["job_id"]


def main() -> None:
    jid = first_job()
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

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"http://localhost:3000/jobs/{jid}", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2000)

        print("=== 初始状态（什么都没做）===")
        tabs = page.locator('[role="tab"]')
        print(f"  tab 数量: {tabs.count()}")
        for i in range(tabs.count()):
            t = tabs.nth(i)
            text = (t.inner_text() or "").replace("\n", " ")
            disabled = t.get_attribute("aria-disabled")
            print(f"    [{i + 1}] {text!r}  aria-disabled={disabled}")

        # 点招呼语（应该被锁）—— aria-disabled 会让 Playwright 判为不可点，用 force 绕过
        print("\n=== 点「招呼语」（没做简历建议，应被拦）===")
        greet_tab = page.get_by_role("tab", name="招呼语")
        greet_tab.click(force=True)
        page.wait_for_timeout(1200)
        body = page.inner_text("body")
        print(f"  出现提示: {'先做「简历建议」' in body}")
        page.screenshot(path=str(OUT / "step-locked.png"), full_page=False)

        # 做匹配度
        print("\n=== 生成匹配度 ===")
        page.get_by_role("button", name="分析匹配度").click()
        page.wait_for_timeout(45000)
        body = page.inner_text("body")
        print(f"  匹配度出来: {'缺口' in body}")
        # 检查简历建议是否解锁
        rw_tab = page.get_by_role("tab", name="简历建议")
        print(f"  简历建议 aria-disabled: {rw_tab.get_attribute('aria-disabled')}")
        greet_tab2 = page.get_by_role("tab", name="招呼语")
        print(f"  招呼语 aria-disabled: {greet_tab2.get_attribute('aria-disabled')}")

        page.screenshot(path=str(OUT / "step-after-match.png"), full_page=False)
        browser.close()


if __name__ == "__main__":
    main()
