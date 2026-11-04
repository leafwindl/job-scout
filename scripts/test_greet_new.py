"""测试新招呼语流程：JD 职责要求 + 简历改写建议 + 简历摘要。"""

from __future__ import annotations

import json
import sqlite3
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT job_id, title, company FROM postings "
    "WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()

print(f"岗位: {row['title']} ｜ {row['company']}\n")

r = post("/greet", {"job_id": row["job_id"], "extra": ""})
print(f"=== 招呼语 {r['chars']} 字 ===")
print(f"  used_code: {r.get('used_code')}  used_brief: {r.get('used_brief')}")
print()
print(r["greeting"])
