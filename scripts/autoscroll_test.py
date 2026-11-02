"""自动滚轮采集：附着到已打开的页面，用真实滚轮往下翻并记录。

不导航、不新建标签。只动鼠标滚轮。
"""

from __future__ import annotations

from job_scout.tools.cdp import CdpCollector

COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"

col = CdpCollector(port=9222, match="joblist.json")
try:
    page = col.attach()
    print("已附着:", page.url[:100])
    print("初始捕获:", len(col.captured))

    try:
        print("初始卡片:", page.evaluate(COUNT), " scrollY:", page.evaluate("window.scrollY"))
    except Exception as e:
        print("读 DOM 失败:", type(e).__name__)

    for i in range(12):
        added = col.wheel_scroll(clicks=1, delta=1000, gap_s=1.8)
        try:
            y = page.evaluate("window.scrollY")
            cards = page.evaluate(COUNT)
        except Exception:
            y, cards = "?", "?"
        print(f"  滚 {i + 1:>2}: 新增响应={added:<2} 累计={len(col.captured):<3} "
              f"scrollY={y} cards={cards}")
        if not col.has_more() and len(col.captured) > 2:
            print("  hasMore=false，到底了")
            break
finally:
    col.close()

print("\n最终捕获:", len(col.captured), "个响应")
