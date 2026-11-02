"""看翻页有没有真的往前走：统计每次响应的 page 参数和去重后的岗位数。"""

from __future__ import annotations

import json
import re
from collections import Counter

raw = json.loads(open("data/raw/boss_api_capture.json", encoding="utf-8").read())

print("响应数:", len(raw))
pages: list[int] = []
ids: list[str] = []
for item in raw:
    url = item.get("url", "")
    m = re.search(r"[?&]page=(\d+)", url)
    page = int(m.group(1)) if m else -1
    pages.append(page)
    jobs = ((item.get("data") or {}).get("zpData") or {}).get("jobList") or []
    for j in jobs:
        ids.append(j.get("encryptJobId") or "")

print("page 分布:", dict(sorted(Counter(pages).items())))
print("岗位条目总数:", len(ids))
print("不同 encryptJobId:", len(set(ids)))
print("平均每响应条数:", round(len(ids) / len(raw), 1) if raw else 0)

print("\n前 8 条 URL:")
for item in raw[:8]:
    u = item.get("url", "")
    u = re.sub(r"&_=\d+", "", u)
    print("  ", u[:150])
