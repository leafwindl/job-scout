"""验证盘符列表与目录浏览。"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode())


print("=== 根：盘符列表 ===")
d = get("/code/browse")
print(f"  可访问盘符: {[x['name'] for x in d['dirs']]}")
print(f"  提示: {d.get('note')}")

if d["dirs"]:
    drive = d["dirs"][0]["path"]
    print(f"\n=== 进入 {drive} ===")
    d2 = get("/code/browse?path=" + urllib.parse.quote(drive))
    names = [x["name"] for x in d2["dirs"]]
    print(f"  {len(names)} 个目录: {names[:8]}")
    if d2.get("error"):
        print(f"  错误: {d2['error']}")

    # 再进一层
    if d2["dirs"]:
        sub = d2["dirs"][0]["path"]
        print(f"\n=== 进入 {sub} ===")
        d3 = get("/code/browse?path=" + urllib.parse.quote(sub))
        print(f"  {len(d3['dirs'])} 个目录: {[x['name'] for x in d3['dirs'][:8]]}")
        if d3.get("error"):
            print(f"  错误: {d3['error']}")
