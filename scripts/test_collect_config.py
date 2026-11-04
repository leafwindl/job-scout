"""测试采集设置：Web 端与油猴脚本共用同一份配置。"""

from __future__ import annotations

import json
import urllib.request

API = "http://127.0.0.1:8001"
COLLECT = "http://127.0.0.1:8766"


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode())


def post(url: str, body: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


print("=== 默认配置 ===")
print(" ", get(API + "/collect/config")["config"])

print("\n=== 改：only_relevant=False, target=50 ===")
r = post(API + "/collect/config", {"only_relevant": False, "target": 50})
print(" ", r["config"])

print("\n=== 脚本侧（8766）看到的 ===")
c = get(COLLECT + "/config")["config"]
print(" ", c)
print("  同步成功:", c["only_relevant"] is False and c["target"] == 50)

print("\n=== 改回默认 ===")
r = post(API + "/collect/config", {"only_relevant": True, "target": 0})
print(" ", r["config"])
