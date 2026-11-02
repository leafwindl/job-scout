"""正确地驱动搜索框：真实按键输入 + 回车。

关键点：不要用 fill()。
fill() 只改 DOM 的 value，React 受控组件感知不到，下一次重渲染就清空。
要用 press_sequentially()，它逐个发真实按键事件。
"""

from __future__ import annotations

import time

from job_scout.tools.cdp import CdpCollector

KEY = "Agent开发"


def main() -> None:
    col = CdpCollector(port=9222, match="joblist.json")
    try:
        page = col.attach(keyword="zhipin.com")
        print("起始:", page.url[:100])

        inp = page.locator("input.ipt-search").first
        inp.wait_for(state="visible", timeout=10_000)

        inp.click()
        page.wait_for_timeout(400)

        # 清空旧内容（全选后删除），再逐字输入
        inp.press("Control+A")
        inp.press("Backspace")
        page.wait_for_timeout(200)
        inp.press_sequentially(KEY, delay=90)
        page.wait_for_timeout(500)

        print("输入框实际值:", repr(inp.input_value()))

        before = len(col.captured)
        inp.press("Enter")
        print("已回车")

        deadline = time.time() + 25
        while time.time() < deadline:
            if "web/geek/jobs" in page.url and len(col.captured) > before:
                break
            col.pump(1)

        print("当前 url:", page.url[:110])
        print("捕获响应:", len(col.captured) - before)
        try:
            print("卡片数:", page.evaluate("document.querySelectorAll('.job-card-wrapper').length"))
        except Exception as e:
            print("读卡片失败:", type(e).__name__)
    finally:
        col.close()


if __name__ == "__main__":
    main()
