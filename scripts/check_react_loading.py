"""验证简历建议的 ReAct 加载状态。"""

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

        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"http://localhost:3000/jobs/{jid}", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(1500)

        # 先做匹配度解锁
        print("生成匹配度（解锁简历建议）…")
        page.get_by_role("button", name="分析匹配度").click()
        page.wait_for_timeout(40000)

        # 点简历建议
        print("点简历建议，观察加载状态…")
        page.get_by_role("tab", name="简历建议").click()
        page.wait_for_timeout(6000)

        body = page.inner_text("body")
        checks = {
            "标题「正在读你的项目代码」": "正在读你的项目代码" in body,
            "阶段「挑选最相关的项目」": "挑选最相关的项目" in body,
            "提示「1–1.5 分钟」": "1–1.5 分钟" in body,
            "秒数计数": "s" in body,
        }
        print("\n=== 加载状态检查 ===")
        for k, v in checks.items():
            print(f"  {k}: {v}")

        page.screenshot(path=str(OUT / "react-loading.png"), full_page=False)
        print("\n  已截图 data/ui-check/react-loading.png")

        # 等它跑完，看最终结果
        print("\n等 ReAct 跑完（最多 180 秒）…")
        page.wait_for_selector("text=重新生成", timeout=180000)
        page.wait_for_timeout(1500)

        body2 = page.inner_text("body")
        print("\n=== 结果检查 ===")
        for kw in ("已参考你提交的项目代码", "项目顺序建议", "建议补充", "建议弱化"):
            print(f"  「{kw}」: {kw in body2}")

        page.screenshot(path=str(OUT / "react-done.png"), full_page=False)
        print("  已截图 data/ui-check/react-done.png")

        browser.close()


if __name__ == "__main__":
    main()
