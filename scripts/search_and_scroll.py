"""真人式搜索：定位搜索框 → 填关键词 → 回车（不行就点搜索按钮）→ 滚轮下翻。"""

from __future__ import annotations

import time

from job_scout.tools.cdp import CdpCollector

KEY = "Agent开发"
COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"


def main() -> None:
    col = CdpCollector(port=9222, match="joblist.json")
    try:
        page = col.attach(keyword="zhipin.com")
        print("起始页:", page.url[:100])

        # 关掉可能展开的下拉
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

        inp = page.locator("input.ipt-search").first
        inp.wait_for(state="visible", timeout=10_000)
        inp.click()
        page.wait_for_timeout(300)
        inp.fill(KEY)
        page.wait_for_timeout(400)
        print("已填入:", inp.input_value())

        before = len(col.captured)
        inp.press("Enter")
        print("已回车，等待跳转…")

        deadline = time.time() + 25
        while time.time() < deadline and "web/geek/jobs" not in page.url:
            col.pump(1)

        if "web/geek/jobs" not in page.url:
            print("回车没跳转，尝试点「搜索」按钮")
            try:
                page.get_by_text("搜索", exact=True).first.click(timeout=5000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print("点按钮失败:", type(e).__name__, str(e)[:60])

        print("当前 url:", page.url[:110])

        deadline = time.time() + 25
        while time.time() < deadline and len(col.captured) == before:
            col.pump(1)

        print("捕获响应:", len(col.captured))
        try:
            print("卡片数:", page.evaluate(COUNT))
        except Exception as e:
            print("读卡片失败:", type(e).__name__)

        for i in range(12):
            added = col.wheel_scroll(clicks=1, delta=1000, gap_s=2.0)
            try:
                y = page.evaluate("window.scrollY")
                c = page.evaluate(COUNT)
            except Exception:
                y, c = "?", "?"
            print(f"  滚 {i + 1:>2}: 新响应={added:<2} 累计={len(col.captured):<3} "
                  f"scrollY={y} cards={c}")

        try:
            page.screenshot(path="data/raw/_search_result2.png", timeout=8000)
        except Exception as e:
            print("截图失败:", type(e).__name__)
    finally:
        col.close()


if __name__ == "__main__":
    main()
