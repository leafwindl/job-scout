"""模拟 BOSS 页面里的油猴脚本，带 Origin 头调用 /analyze。"""

from __future__ import annotations

import json
import sqlite3
import urllib.request

BASE = "http://127.0.0.1:8001"

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT title, company, description, district FROM postings "
    "WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()

body = {
    "title": row["title"] or "",
    "company": row["company"] or "",
    "city": row["district"] or "",
    "jd": (row["description"] or "")[:12000],
}

for origin in ("https://www.zhipin.com", "http://localhost:3000"):
    req = urllib.request.Request(
        BASE + "/analyze",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Origin": origin},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.loads(r.read().decode())
            allow = r.headers.get("access-control-allow-origin")
        print(f"  Origin {origin}")
        print(f"    allow-origin: {allow}")
        print(f"    分数: {d['score']}  判断: {d['verdict']}")
    except Exception as e:  # noqa: BLE001
        print(f"  Origin {origin} 失败: {e}")
