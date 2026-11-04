"""验证目录浏览、项目发现、批量扫描、对照审查。"""

from __future__ import annotations

import json
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=60) as r:
        return json.loads(r.read().decode())


def post(path: str, body: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


print("=== 1. 目录浏览 ===")
d = get("/code/browse?path=F:/project_work")
print(f"  {d['path']}  子目录 {len(d['dirs'])} 个")
projects = [x for x in d["dirs"] if x["is_project"]]
print(f"  其中识别为项目: {len(projects)} 个 -> {[x['name'] for x in projects]}")

print("\n=== 2. 自动发现 ===")
r = get("/code/discover?path=F:/project_work")
print(f"  发现 {len(r['items'])} 个: {[x['name'] for x in r['items']]}")

print("\n=== 3. 批量扫描（只挑两个，别扫太多）===")
names = [x["name"] for x in r["items"]][:2]
res = post("/code/scan-many", {"path": "F:/project_work", "only": names})
print(f"  扫描 {res['total']} 个，成功 {res['ok_count']} 个")
for x in res["items"]:
    if x["ok"]:
        print(f"    ✓ {x['name']}  {x['file_count']} 文件 / {x['line_count']} 行")
    else:
        print(f"    ✗ {x['name']}  {x.get('error')}")

print("\n=== 4. 对照审查（拿 job-scout 项目）===")
try:
    rv = post("/code/review", {"project": "AI 求职助手"}, timeout=300)
    print(f"  项目: {rv['project']}")
    print(f"  判断: {rv['verdict'][:120]}")
    print(f"  不符 {len(rv['inaccurate'])} 条 / 遗漏 {len(rv['missing'])} 条 / 改写 {len(rv['rewrites'])} 条")
    for x in rv["missing"][:2]:
        print(f"    + {x['fact'][:50]} -> {x['suggest'][:50]}")
except Exception as e:  # noqa: BLE001
    print(f"  失败: {e}")
