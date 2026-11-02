"""关掉烂标签，开全新标签，测试键盘滚动能否触发懒加载。"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

URL = "https://www.zhipin.com/web/geek/jobs?query=Agent%E5%BC%80%E5%8F%91&city=101280100"
COUNT = "document.querySelectorAll('.job-card-wrapper, .job-card-box').length"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

# 1. 关掉所有职位搜索页（留首页，避免关掉最后一个标签导致浏览器退出）
for p in list(ctx.pages):
    try:
        if "zhipin.com/web/geek/jobs" in p.url and len(ctx.pages) > 1:
            p.close()
            print("已关闭旧标签:", p.url[:60])
    except Exception:
        pass

# 2. 开全新标签
page = ctx.new_page()
print("新标签已创建")
page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
page.wait_for_timeout(5000)

print("初始 cards =", page.evaluate(COUNT), " scrollY =", page.evaluate("window.scrollY"))

# 3. 点列表区域拿焦点，再用真实按键滚动
page.mouse.click(420, 420)
page.wait_for_timeout(600)

prev = page.evaluate(COUNT)
for i in range(8):
    try:
        page.keyboard.press("End")
        page.wait_for_timeout(2000)
        cards = page.evaluate(COUNT)
        y = page.evaluate("window.scrollY")
        print(f"  End #{i + 1}: scrollY={y:<6} cards={cards}")
    except Exception as e:
        print(f"  End #{i + 1} 出错:", type(e).__name__, str(e)[:70])
        page.wait_for_timeout(2000)

print("最终 cards =", page.evaluate(COUNT))

try:
    page.screenshot(path="data/raw/_fresh_state.png", timeout=10_000)
    print("screenshot ok")
except Exception as e:
    print("截图失败:", type(e).__name__)

pw.stop()
