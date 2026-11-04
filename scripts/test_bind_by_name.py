"""验证：用简历里的项目名绑定代码目录，再对照审查。"""

from __future__ import annotations

import json
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


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode())


# 简历里的真实项目名
RESUME_PROJECT = "Echo AI 助手 App —— Agent 工具调度与长期记忆"

print("=== 1. 用简历项目名扫描 AI_Chat 目录 ===")
r = post(
    "/code/scan",
    {"path": "F:/project_work/AI_Chat", "project_name": RESUME_PROJECT},
    timeout=600,
)
print(f"  project_name: {r['project_name']}")
print(f"  规模: {r['file_count']} 文件 / {r['line_count']} 行")
print(f"  依赖: {r['deps'][:6]}")

print("\n=== 2. 列表确认绑定 ===")
for x in get("/code")["items"]:
    exact = "✓" if x["project_name"] == RESUME_PROJECT else " "
    print(f"  {exact} {x['project_name'][:44]}")

print("\n=== 3. 对照审查（这次名字是精确的）===")
rv = post("/code/review", {"project": RESUME_PROJECT}, timeout=300)
print(f"  项目: {rv['project'][:40]}")
print(f"  判断: {rv['verdict'][:160]}")
print(f"  不符 {len(rv['inaccurate'])} / 遗漏 {len(rv['missing'])} / 改写 {len(rv['rewrites'])}")
for x in rv["missing"][:2]:
    print(f"    + {x['fact'][:46]}")
    print(f"      可补: {x['suggest'][:60]}")
