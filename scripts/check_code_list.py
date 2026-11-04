"""验证「项目代码」卡片是否直接列出简历里的项目。"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("data/ui-check")
OUT.mkdir(parents=True, exist_ok=True)


def resume_projects() -> list[str]:
    with urllib.request.urlopen("http://127.0.0.1:8001/profile", timeout=20) as r:
        p = json.loads(r.read().decode())
    return [x.get("name", "") for x in (p.get("projects") or []) if x.get("name")]


def main() -> None:
    names = resume_projects()
    print("简历里的项目:")
    for n in names:
        print(f"  - {n}")

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
        page.goto("http://localhost:3000/profile", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(2500)

        body = page.inner_text("body")
        print("\n=== 检查 ===")
        for n in names:
            short = n[:20]
            print(f"  列表里有「{short}」: {short in body}")
        print(f"  「选择文件夹」按钮: {body.count('选择文件夹')} 个")
        print(f"  「对照审查」按钮: {body.count('对照审查')} 个")

        page.evaluate("document.getElementById('project-code')?.scrollIntoView()")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "code-list.png"), full_page=False)
        print("\n  已截图 data/ui-check/code-list.png")

        browser.close()


if __name__ == "__main__":
    main()
