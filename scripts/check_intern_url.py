"""验证采集 URL 带 intern=1，且脚本能探测到 8766。"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


print("=== /collect/start（intern=True）===")
r = post("/collect/start", {"keyword": "Agent", "city": "广州", "intern": True})
print(f"  url: {r['url']}")
print(f"  含 intern=1: {'intern=1' in r['url']}")

print("\n=== /collect/start（intern=False）===")
r2 = post("/collect/start", {"keyword": "Agent", "city": "广州", "intern": False})
print(f"  url: {r2['url']}")
print(f"  含 intern=1: {'intern=1' in r2['url']}")

print("\n=== 采集接收服务 8766 ===")
with urllib.request.urlopen("http://127.0.0.1:8766/health", timeout=10) as h:
    d = json.loads(h.read().decode())
print(f"  {d}")
print(f"  是我们的服务（有 total）: {'total' in d}")
