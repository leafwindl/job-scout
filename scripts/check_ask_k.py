"""验证提高上下文预算后，引用条数是否变多。"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def ask(question: str, k: int) -> dict:
    body = json.dumps({"question": question, "k": k}).encode()
    req = urllib.request.Request(
        f"{BASE}/ask", data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


q = "广州有哪些 Agent 相关实习岗？"
for k in (5, 8, 12):
    d = ask(q, k)
    print(f"k={k:2d} -> 实际参考 {d['docs_count']} 条，引用 {len(d['citations'])} 条")
    for c in d["citations"]:
        print(f"        [{c['index']}] {c.get('title', '')[:32]}")
    print()
