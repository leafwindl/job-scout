"""诊断：BOSS 职位列表到底挂在哪个可滚动容器上。

只做只读操作（读 DOM、滚一下看元素数量变化），不导航、不发请求。
"""

from __future__ import annotations

from playwright.sync_api import sync_playwright

FIND_SCROLLERS = """
(() => {
  const out = [];
  document.querySelectorAll('*').forEach(el => {
    const st = getComputedStyle(el);
    const scrollable = (st.overflowY === 'auto' || st.overflowY === 'scroll')
                        && el.scrollHeight > el.clientHeight + 20;
    if (scrollable || el.scrollHeight > window.innerHeight + 200) {
      out.push({
        tag: el.tagName.toLowerCase(),
        cls: (el.className || '').toString().slice(0, 60),
        sh: el.scrollHeight,
        ch: el.clientHeight,
        oy: st.overflowY,
      });
    }
  });
  return out.sort((a, b) => b.sh - a.sh).slice(0, 12);
})()
"""

COUNT_CARDS = "document.querySelectorAll('li.job-card-wrapper, .job-card-wrapper, .job-card-box').length"

pw = sync_playwright().start()
b = pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
ctx = b.contexts[0]

page = None
for p in ctx.pages:
    if "zhipin.com/web/geek/jobs" in p.url:
        page = p
        break

if page is None:
    print("没找到已打开的职位搜索页。请在浏览器里打开搜索页再跑这个脚本。")
    pw.stop()
    raise SystemExit(0)

print("page:", page.url[:100])
print("body scrollHeight:", page.evaluate("document.body.scrollHeight"))
print("window.innerHeight:", page.evaluate("window.innerHeight"))
print("卡片数(滚动前):", page.evaluate(COUNT_CARDS))

print("\n可滚动候选:")
for row in page.evaluate(FIND_SCROLLERS):
    print(f"  <{row['tag']}> sh={row['sh']:<7} ch={row['ch']:<6} oy={row['oy']:<7} class={row['cls']}")

# 滚一下 window，看卡片是否增加
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
page.wait_for_timeout(3500)
print("\n卡片数(滚 window 后):", page.evaluate(COUNT_CARDS))
print("当前滚动位置:", page.evaluate("window.scrollY"))

pw.stop()
