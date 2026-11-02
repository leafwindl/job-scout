"""验证：URL 加 &page=N 能不能让页面自己请求第 N 页。"""

from __future__ import annotations

import time

from job_scout.tools.cdp import CdpCollector

BASE = (
    "https://www.zhipin.com/web/geek/jobs"
    "?query=Agent%E5%BC%80%E5%8F%91&city=101280100&industry=&position="
)


def wait_growth(col: CdpCollector, before: int, timeout_s: int = 20) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if len(col.captured) > before:
            return True
        col.pump(1)
    return False


col = CdpCollector(port=9222, match="joblist.json")
seen_all: dict[str, int] = {}
try:
    # 先打开第 1 页，让 col.page 有值
    col.open(f"{BASE}&page=1")
    col.wait_for_data(timeout_s=25)

    for n in range(1, 6):
        before = len(col.captured)
        url = f"{BASE}&page={n}"
        if n > 1:
            try:
                col.goto(url)
            except Exception as e:
                print(f"page {n}: 导航失败 {type(e).__name__} {str(e)[:60]}")
                continue

        got = wait_growth(col, before, timeout_s=25)
        new_items = col.captured[before:]
        ids: list[str] = []
        for item in new_items:
            for j in ((item.get("data") or {}).get("zpData") or {}).get("jobList") or []:
                ids.append(j.get("encryptJobId") or "")

        for i in ids:
            if i:
                seen_all[i] = seen_all.get(i, 0) + 1

        print(f"page {n}: 新响应={len(new_items):<2} 岗位条目={len(ids):<3} "
              f"不同id={len(set(ids)):<3} 累计不同={len(seen_all)}  (收到数据={got})")
        time.sleep(2)
finally:
    col.close()

print("\n最终不同岗位:", len(seen_all))
