"""看一眼捕获到的原始接口响应长什么样。"""

from __future__ import annotations

import json
from pathlib import Path

p = Path("data/raw/boss_api_capture.json")
data = json.loads(p.read_text(encoding="utf-8"))
print("payloads:", len(data))
for i, pay in enumerate(data):
    print(f"\n[{i}] top keys: {list(pay.keys())}")
    print("  code:", pay.get("code"), "message:", pay.get("message"))
    zp = pay.get("zpData") or {}
    print("  zpData keys:", list(zp.keys())[:15])
    jobs = zp.get("jobList") or []
    print("  jobList:", len(jobs))
    if jobs:
        j = jobs[0]
        print("  job keys:", list(j.keys()))
        for k in ("jobName", "salaryDesc", "brandName", "cityName", "areaDistrict", "skills"):
            print(f"    {k} = {j.get(k)!r}")
