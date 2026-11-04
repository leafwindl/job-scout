"""测试打招呼语的「提建议重写」。"""

from __future__ import annotations

import json
import sqlite3
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, timeout: int = 300) -> dict:
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

print("=== 1. 生成原始招呼语 ===")
g = post("/greet", {"job_id": row["job_id"], "extra": ""})
print(f"  {g['chars']} 字")
print(f"  {g['greeting']}")

cur = g["greeting"]

for fb in ("太长了，压缩到 100 字以内", "别提薪资，强调我的 RAG 项目"):
    print(f"\n=== 2. 反馈：{fb} ===")
    r = post("/greet/revise", {
        "job_id": row["job_id"],
        "current": cur,
        "feedback": fb,
    })
    print(f"  {r['chars']} 字（原 {len(cur)} 字）")
    print(f"  {r['greeting']}")
