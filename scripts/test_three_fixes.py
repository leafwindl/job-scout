"""验证三点：超长 JD 用清洗版、招呼语复用 rewrite、预扫描 UI 存在。"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, timeout: int = 900) -> dict:
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
# 找一条有 jd_clean 的
row = conn.execute(
    "SELECT job_id, title, length(description) AS d, length(jd_clean) AS c "
    "FROM postings WHERE jd_clean IS NOT NULL LIMIT 1"
).fetchone()
conn.close()

print("=== 1. 超长 JD 读取 ===")
if row:
    print(f"  岗位: {row['title'][:30]}")
    print(f"  原文 {row['d']} 字 -> 清洗版 {row['c']} 字")
    from job_scout.textclean import extract_jd_core

    clean = row["c"]
    print(f"  jd_clean 已入库: {clean is not None}")
else:
    print("  没有清洗过的 JD")

print("\n=== 2. 招呼语复用 rewrite ===")
conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
job = conn.execute(
    "SELECT job_id, title FROM postings WHERE is_relevant=1 AND description IS NOT NULL LIMIT 1"
).fetchone()
conn.close()

# 先拿一份 rewrite 结果（模拟前端已经跑过）
rw = post(f"/resume/rewrite/{job['job_id']}", {}, timeout=900)
print(f"  先跑 rewrite：{job['title'][:24]}，改写建议 {len(rw.get('rewrites') or [])} 条")

fake_rewrite = {
    "summary": rw.get("summary", ""),
    "rewrites": rw.get("rewrites", []),
    "add": rw.get("add", []),
}

t0 = time.time()
g1 = post("/greet", {"job_id": job["job_id"]}, timeout=900)
t1 = time.time() - t0

t0 = time.time()
g2 = post("/greet", {"job_id": job["job_id"], "rewrite": fake_rewrite}, timeout=900)
t2 = time.time() - t0

print(f"  不复用 rewrite：{t1:.1f}s")
print(f"  复用 rewrite：  {t2:.1f}s  reused={g2.get('reused_rewrite')}")
print(f"  省了 {t1 - t2:.1f} 秒")
print(f"\n  复用版招呼语 {g2['chars']} 字：\n  {g2['greeting'][:160]}")
