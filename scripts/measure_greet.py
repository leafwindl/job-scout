"""量化招呼语生成：几次 LLM 调用、总耗时多少。"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.request

BASE = "http://127.0.0.1:8001"

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT job_id, title FROM postings WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()

req = urllib.request.Request(
    BASE + "/greet",
    data=json.dumps({"job_id": row["job_id"], "extra": ""}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

t0 = time.time()
with urllib.request.urlopen(req, timeout=900) as r:
    d = json.loads(r.read().decode())
elapsed = time.time() - t0

print(f"岗位: {row['title']}")
print(f"总耗时: {elapsed:.1f} 秒")
print(f"招呼语: {d['chars']} 字")
print()
print(d["greeting"])
