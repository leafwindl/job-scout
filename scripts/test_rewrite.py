"""测试简历改写建议（API 层）。"""

from __future__ import annotations

import json
import urllib.request


def get(p: str):
    with urllib.request.urlopen(f"http://127.0.0.1:8001{p}", timeout=20) as r:
        return json.loads(r.read().decode())


def post(p: str, body: dict | None = None):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:8001{p}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


jobs = get("/jobs?size=40")
# 挑一个 Agent/RAG 相关的
target = None
for it in jobs["items"]:
    if "Agent" in it["title"] or "agent" in it["title"]:
        target = it
        break
target = target or jobs["items"][0]

print(f"岗位: {target['title']} ｜ {target['company']}")
print("=" * 66)

m = post(f"/match/{target['job_id']}")
print(f"匹配: {m['score']} 分 · {m['verdict']}\n")

r = post(f"/resume/rewrite/{target['job_id']}")
print("【总结】", r.get("summary"))
print("\n【项目顺序】", " → ".join(r.get("reorder") or []))
print("\n【具体改写】")
for x in r.get("rewrites") or []:
    print(f"  · {x.get('project', '')}")
    print(f"    原: {x.get('original', '')[:80]}")
    print(f"    改: {x.get('suggested', '')[:120]}")
    print(f"    因: {x.get('why', '')[:100]}")
print("\n【建议补充】")
for x in r.get("add") or []:
    print(f"  + {x}")
print("\n【建议弱化】")
for x in r.get("cut") or []:
    print(f"  - {x}")
