"""探测：哪个容器滚动能触发页面自己的翻页请求。"""

from __future__ import annotations

from urllib.parse import quote

from job_scout.tools.cdp import CdpCollector

URL = f"https://www.zhipin.com/web/geek/jobs?query={quote('Agent开发')}&city=101280100"

TARGETS = [
    ("window", "window.scrollTo(0, document.body.scrollHeight)"),
    (".job-list-box", "document.querySelector('.job-list-box')?.scrollTo(0, 999999)"),
    (".job-list-container", "document.querySelector('.job-list-container')?.scrollTo(0, 999999)"),
    (".job-list", "document.querySelector('.job-list')?.scrollTo(0, 999999)"),
    ("scroller", "document.scrollingElement.scrollTop = 999999"),
]


def main() -> None:
    col = CdpCollector(port=9222, match="joblist.json")
    try:
        col.open(URL)
        ok = col.wait_for_data(timeout_s=30)
        print("initial captured:", len(col.captured), "ok:", ok)
        print("url:", col.url())

        for name, js in TARGETS:
            before = len(col.captured)
            for _ in range(3):
                col.page.evaluate(js)
                col.page.wait_for_timeout(2500)
            print(f"  {name:22} -> 新增 {len(col.captured) - before}")

        # 看看页面上有没有「加载更多」之类
        text = col.body_text()
        for kw in ("加载更多", "查看更多", "下一页", "没有更多"):
            if kw in text:
                print("页面出现关键词:", kw)
    finally:
        col.close()


if __name__ == "__main__":
    main()
