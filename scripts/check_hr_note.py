"""验证简历建议里显示 HR 视角。"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
OUT.mkdir(parents=True, exist_ok=True)


def first_job() -> str:
    conn = sqlite3.connect("data/job_scout.db")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT job_id FROM postings WHERE is_relevant=1 AND description IS NOT NULL LIMIT 1"
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

        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.goto(f"http://localhost:3000/jobs/{jid}", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(1500)

        print("生成匹配度…")
        page.get_by_role("button", name="分析匹配度").click()
        page.wait_for_timeout(40000)

        print("点简历建议（会自动跑 ReAct，约 90 秒）…")
        page.get_by_role("tab", name="简历建议").click()
        page.wait_for_selector("text=重新生成", timeout=240000)
        page.wait_for_timeout(1500)

        body = page.inner_text("body")
        print("\n=== 检查 ===")
        for kw in ("HR 视角", "具体改写", "建议补充"):
            print(f"  「{kw}」: {kw in body}")
        print(f"  「HR 视角」出现次数: {body.count('HR 视角')}")

        page.evaluate("window.scrollTo(0, 900)")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUT / "hr-note.png"), full_page=False)
        print("\n  已截图 data/ui-check/hr-note.png")

        browser.close()


if __name__ == "__main__":
    main()
