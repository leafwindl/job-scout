"""纯监听模式：不导航、不滚动、不点任何东西。

你在浏览器里自己搜索、自己往下滚，这个脚本只做两件事：
  1. 听页面自己发出的 joblist 请求
  2. 有新数据就解析入库（幂等，重复跑没关系）

用法：
    uv run python scripts/listen.py            # 默认挂 30 分钟
    uv run python scripts/listen.py 60         # 挂 60 分钟
"""

from __future__ import annotations

import sys
import time

from job_scout.config import settings
from job_scout.sources.boss import BossAdapter, RiskControlError
from job_scout.storage import Storage
from job_scout.tools.cdp import CdpCollector

MINUTES = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def main() -> None:
    adapter = BossAdapter()
    store = Storage(settings.db_path)

    col = CdpCollector(port=9222, match="joblist.json")
    try:
        page = col.attach(keyword="zhipin.com")
        print(f"已监听: {page.url[:90]}", flush=True)
        print("现在请在浏览器里搜索 + 往下滚动，这边会自动记录。Ctrl+C 结束。", flush=True)

        saved = 0
        last = 0
        deadline = time.time() + MINUTES * 60

        while time.time() < deadline:
            n = len(col.captured)
            if n > last:
                last = n
                postings = []
                for payload in col.payloads():
                    try:
                        postings.extend(adapter.parse_api_joblist(payload))
                    except RiskControlError as e:
                        print(f"  [风控] {e}", flush=True)
                        continue
                    except ValueError:
                        continue
                merged = {p.dedupe_key: p for p in postings}
                new = 0
                for p in merged.values():
                    if store.upsert(p):
                        new += 1
                saved = store.count()
                total = col.total_count()
                print(
                    f"  响应 {n} 个 → 本批 {len(merged)} 条，新增 {new} 条，"
                    f"库内共 {saved} 条" + (f"（接口总量 {total}）" if total else ""),
                    flush=True,
                )
            col.pump(2)
    except KeyboardInterrupt:
        print("\n结束监听", flush=True)
    finally:
        col.close()
        store.close()


if __name__ == "__main__":
    main()
