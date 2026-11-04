"""对比：招呼语带代码实况 vs 不带。"""

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

g = post("/greet", {"job_id": row["job_id"], "extra": ""})
print(f"=== 新版（带项目代码实况）{g['chars']} 字 ===")
print(f"  used_code: {g.get('used_code')}")
print(f"  {g['greeting']}")

# 看有没有引用代码里的具体事实
facts = [
    "/login/phone", "Blufi", "pgvector", "provisioning", "pairing",
    "router", "SSE", "混合检索", "RRF", "knowledge graph", "知识图谱",
]
hits = [f for f in facts if f.lower() in g["greeting"].lower()]
print(f"\n  引用了代码事实: {hits if hits else '（无）'}")
