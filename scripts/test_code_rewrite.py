"""测试 /code/scan 与改写联动。"""

from __future__ import annotations

import json
import sqlite3
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode())


print("=== 扫描 job-scout 项目 ===")
d = post("/code/scan", {"path": "F:/Project_do/Agent/job-scout", "project_name": "AI 求职助手"})
print(f"  项目: {d['project_name']}  slug={d['slug']}")
print(f"  规模: {d['file_count']} 文件 / {d['line_count']} 行")
print(f"  语言: {d['langs']}")
print(f"  依赖: {d['deps'][:8]}")
print(f"  摘要: {len(d['summary'])} 字")

print("\n=== 已保存列表 ===")
for it in get("/code")["items"]:
    print(f"  · {it['project_name']}  {it['file_count']} 文件  {it['line_count']} 行")

print("\n=== 摘要预览 ===")
print("\n".join("  " + x for x in d["summary"].splitlines()[:12]))

print("\n=== 带代码改写简历 ===")
conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
row = conn.execute(
    "SELECT job_id, title FROM postings WHERE description IS NOT NULL AND is_relevant=1 LIMIT 1"
).fetchone()
conn.close()
print(f"  目标岗位: {row['title']}")
proj = urllib.parse.quote("AI 求职助手")
r = post(f"/resume/rewrite/{row['job_id']}?project={proj}", {}, timeout=180)
print(f"  用了代码摘要: {r.get('used_code')}")
print(f"  总结: {r.get('summary', '')[:100]}")
for x in (r.get("rewrites") or [])[:2]:
    print(f"  · 原: {x.get('original', '')[:40]}")
    print(f"    改: {x.get('suggested', '')[:70]}")
    print(f"    由: {x.get('why', '')[:60]}")
