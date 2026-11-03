"""抽查容器 API 返回的 JD 是否还有 CSS / 水印。"""

from __future__ import annotations

import json
import re
import urllib.request

BASE = "http://127.0.0.1:8001"

with urllib.request.urlopen(f"{BASE}/jobs?size=40", timeout=20) as r:
    items = json.loads(r.read().decode())["items"]

CSS = re.compile(r"\.[A-Za-z][\w-]*\s*\{")
bad = 0
checked = 0
for it in items:
    with urllib.request.urlopen(f"{BASE}/jobs/{it['job_id']}", timeout=20) as r2:
        j = json.loads(r2.read().decode())
    desc = j.get("description") or ""
    if not desc:
        continue
    checked += 1
    hit = CSS.search(desc) or "kanzhun" in desc
    if hit:
        bad += 1
        print(f"  仍有脏数据: {j['title'][:30]}")

print(f"\n抽查 {checked} 条有正文的岗位，脏数据 {bad} 条")

# 抽一条看开头
if checked:
    with urllib.request.urlopen(f"{BASE}/jobs/{items[0]['job_id']}", timeout=20) as r3:
        j = json.loads(r3.read().decode())
    print(f"\n样例 [{j['title'][:30]}]:")
    print("  " + (j.get("description") or "")[:180].replace("\n", " "))
