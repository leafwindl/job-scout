"""测试 /analyze 与 /analyze/ask（模拟悬浮窗的调用）。"""

from __future__ import annotations

import json
import sqlite3
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# 取一条真实 JD 当测试素材（模拟用户在 BOSS 上点开的岗位）
conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT title, company, description, district FROM postings "
    "WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()

jd = (row["description"] or "")[:12000]
print(f"测试岗位: {row['title']} ｜ {row['company']} ｜ JD {len(jd)} 字\n")

print("=== /analyze（匹配度）===")
d = post("/analyze", {
    "title": row["title"] or "",
    "company": row["company"] or "",
    "city": row["district"] or "",
    "jd": jd,
})
print(f"  分数: {d['score']}  判断: {d['verdict']}")
print(f"  理由: {d.get('reason', '')[:120]}")
print(f"  匹配 {len(d.get('matched') or [])} 条 / 缺口 {len(d.get('missing') or [])} 条")
for x in (d.get("matched") or [])[:2]:
    print(f"    ✓ {x[:60]}")
for x in (d.get("missing") or [])[:2]:
    print(f"    − {x[:60]}")

print("\n=== /analyze/ask（问一条）===")
a = post("/analyze/ask", {
    "jd": jd,
    "question": "这个岗位我值得投吗？最缺什么？",
})
print(f"  {a['answer'][:260]}")
