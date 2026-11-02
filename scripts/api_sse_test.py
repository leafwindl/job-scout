"""SSE 流式接口 + 延迟测试。"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8001"


def test_sse(question: str) -> None:
    q = urllib.parse.quote(question)
    url = f"{BASE}/ask/stream?q={q}&k=3"
    print(f"=== SSE: {question} ===")
    t0 = time.perf_counter()
    first_token_at = None
    events = []

    with urllib.request.urlopen(url, timeout=60) as r:
        for raw in r:
            line = raw.decode("utf-8").strip()
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
                if line.endswith("token") and first_token_at is None:
                    first_token_at = time.perf_counter() - t0

    total = time.perf_counter() - t0
    print(f"事件序列: {events[:6]}{'...' if len(events) > 6 else ''}")
    print(f"事件总数: {len(events)}")
    print(f"首 token 延迟: {first_token_at:.3f}s" if first_token_at else "无 token 事件")
    print(f"总耗时: {total:.3f}s")
    print(f"顺序正确: {events[0] == 'meta' and events[-1] == 'done'}")


def test_latency(n: int = 5) -> None:
    print(f"\n=== 延迟测试（{n} 次 /search）===")
    times = []
    for i in range(n):
        payload = json.dumps({"query": "Agent 实习", "k": 10}).encode("utf-8")
        req = urllib.request.Request(
            BASE + "/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        times.append((time.perf_counter() - t0) * 1000)

    times.sort()
    p50 = times[len(times) // 2]
    p95 = times[int(len(times) * 0.95) - 1]
    print(f"P50={p50:.0f}ms  P95={p95:.0f}ms  max={times[-1]:.0f}ms")


if __name__ == "__main__":
    test_sse("哪些实习岗要求 LangGraph？")
    test_latency()
