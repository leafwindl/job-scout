"""端到端测 /resume/rewrite：应该自动选项目 + 跑 ReAct。"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.request

BASE = "http://127.0.0.1:8001"

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT job_id, title, company FROM postings WHERE is_relevant=1 AND description IS NOT NULL LIMIT 1"
).fetchone()
conn.close()

print(f"岗位：{row['title']} ｜ {row['company']}")
print("请求中（会跑 ReAct，约 45 秒）…\n")

req = urllib.request.Request(
    f"{BASE}/resume/rewrite/{row['job_id']}", data=b"{}",
    headers={"Content-Type": "application/json"}, method="POST",
)
t0 = time.time()
with urllib.request.urlopen(req, timeout=600) as r:
    d = json.loads(r.read().decode())
elapsed = time.time() - t0

print(f"总耗时 {elapsed:.1f} 秒")
react = d.get("react") or {}
if react:
    print(f"ReAct: 项目={react.get('project')}")
    print(f"  {react.get('turns')} 轮 / {react.get('tool_calls')} 次调用 / "
          f"读 {react.get('files_read')} 个文件 / {react.get('elapsed')}s")
    if react.get("error"):
        print(f"  错误: {react['error']}")

print(f"\n总结：{d.get('summary', '')[:160]}")
print(f"\n改写建议 {len(d.get('rewrites') or [])} 条：")
for x in (d.get("rewrites") or [])[:3]:
    print(f"\n  原文：{(x.get('original') or '')[:60]}")
    print(f"  改后：{(x.get('suggested') or '')[:110]}")
    print(f"  依据：{(x.get('why') or '')[:90]}")
    hr = x.get("hr_note") or ""
    print(f"  HR：{'（模型没给）' if not hr else hr[:90]}")
print(f"\n可补 {len(d.get('add') or [])} 条：")
for x in (d.get("add") or [])[:2]:
    print(f"  + {x[:110]}")
