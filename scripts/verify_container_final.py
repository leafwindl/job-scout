"""容器版最终验证：画像结构 + 结合简历的问答。"""

from __future__ import annotations

import json
import time
import urllib.request

BASE = "http://127.0.0.1:8001"


def get(path: str, timeout: int = 30) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode())


p = get("/profile")
print("=== 画像 ===")
print(f"  姓名: {p.get('name')}  来源: {p.get('source_file')}")
print(f"  技能: {len(p.get('skills') or [])} 项")
for x in p.get("projects") or []:
    print(f"  · {x.get('name')}")
    for b in (x.get("bullets") or [])[:2]:
        print(f"      - {b[:70]}…")

print("\n=== 结合简历的问答（SSE）===")
url = f"{BASE}/ask/stream?q=%E6%88%91%E9%80%82%E5%90%88%E6%8A%95%E5%93%AA%E4%BA%9B%E5%B2%97%E4%BD%8D&k=3&use_profile=1"
t0 = time.time()
events: list[str] = []
chunks: list[str] = []
with urllib.request.urlopen(url, timeout=180) as r:
    for raw in r:
        line = raw.decode("utf-8").strip()
        if line.startswith("event:"):
            events.append(line.split(":", 1)[1].strip())
        elif line.startswith("data:") and events and events[-1] == "token":
            try:
                chunks.append(json.loads(line[5:].strip()))
            except Exception:
                pass

print(f"  事件序列: {events[:5]}… (共 {len(events)})")
print(f"  meta 带 with_profile: {'with_profile' in json.dumps(events)}")
print(f"  首 token 用时: {time.time() - t0:.1f}s")
print(f"  正文前 220 字:\n  {''.join(chunks)[:220]}")
