"""用真实输入事件滚动，验证懒加载会不会触发。

相比 window.scrollTo，键盘 / 滚轮是真实输入事件，
懒加载监听器更容易被触发。
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"
SCROLL_Y = "window.scrollY"
BODY_H = "document.body.scrollHeight"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

page = next((p for p in ctx.pages if "zhipin.com/web/geek/jobs" in p.url), None)
if page is None:
    print("没有职位搜索页，先打开一个")
    pw.stop()
    raise SystemExit(0)

print("url:", page.url[:100])
print(
    f"初始: cards={page.evaluate(COUNT)} scrollY={page.evaluate(SCROLL_Y)} bodyH={page.evaluate(BODY_H)}"
)

# 先点一下列表区域，让页面获得焦点（真实用户滚动前也会先点）
try:
    page.mouse.click(400, 400)
    page.wait_for_timeout(500)
    print("已点击列表区域获取焦点")
except Exception as e:
    print("点击失败:", type(e).__name__)

prev_cards = page.evaluate(COUNT)

for i in range(8):
    try:
        page.keyboard.press("End")
        page.wait_for_timeout(1800)
        cards = page.evaluate(COUNT)
        y = page.evaluate(SCROLL_Y)
        h = page.evaluate(BODY_H)
        print(f"  End #{i + 1}: scrollY={y:<6} bodyH={h:<6} cards={cards}")
        if cards > prev_cards:
            prev_cards = cards

        # End 不奏效就试滚轮
        if y == 0:
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(1200)
            print(f"        wheel -> scrollY={page.evaluate(SCROLL_Y)} cards={page.evaluate(COUNT)}")
    except Exception as e:
        print(f"  #{i + 1} 出错:", type(e).__name__, str(e)[:70])
        page.wait_for_timeout(1500)

print(
    f"最终: cards={page.evaluate(COUNT)} scrollY={page.evaluate(SCROLL_Y)}"
)
pw.stop()
