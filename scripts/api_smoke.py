"""API 冒烟测试：验证四个接口返回正确的中文数据。"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


print("=== /health ===")
print(get("/health"))

print("\n=== /search: LangGraph ===")
res = post("/search", {"query": "LangGraph", "k": 3})
print(f"total={res['total']}")
for h in res["hits"]:
    print(f"  {h['title']} | {h['company']} | score={h['score']:.4f}")

print("\n=== /ask: 哪些实习岗要求 LangGraph？ ===")
ans = post("/ask", {"question": "哪些实习岗要求 LangGraph？", "k": 3})
print(f"mode={ans['mode']} docs={ans['docs_count']} citations={len(ans['citations'])}")
print(ans["answer"][:300])

print("\n=== /jobs 列表 ===")
jobs = get("/jobs?size=3")
print(f"total={jobs['total']}")
for it in jobs["items"]:
    print(f"  {it['title']} | {it['company']} | {it['category']}")

print("\n=== /jobs/{id} 详情 ===")
jid = jobs["items"][0]["job_id"]
detail = get(f"/jobs/{jid}")
print(f"title={detail['title']} jd_len={len(detail['description'])} skills={detail['skills'][:3]}")
