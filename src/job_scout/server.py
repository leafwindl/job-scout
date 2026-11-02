"""本地接收服务：油猴脚本把岗位推到这里，直接入库。

为什么要有它：
- 油猴脚本跑在你自己的浏览器里（真实登录态、无自动化特征）
- 脚本负责「旁听接口 + 收集数据」
- 这个服务负责「收数据 + 去重 + 入库」

只监听 127.0.0.1，不对外暴露。
"""

from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from job_scout.config import settings
from job_scout.models import JobPosting, Source
from job_scout.salary import parse_salary
from job_scout.storage import Storage

HOST = "127.0.0.1"
PORT = 8765

# 自动模式完成标记：油猴脚本抓完 JD 后 POST /auto-done。
# 落文件而不是内存，这样 API 进程和采集进程都能读到（可能不是同一个进程）。
AUTO_DONE_FILE = Path("data/auto_done.json")


def mark_auto_done() -> float:
    at = time.time()
    AUTO_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_DONE_FILE.write_text(json.dumps({"at": at}), encoding="utf-8")
    return at


def read_auto_done() -> float:
    try:
        return float(json.loads(AUTO_DONE_FILE.read_text(encoding="utf-8"))["at"])
    except Exception:
        return 0.0


def to_posting(raw: dict[str, Any]) -> JobPosting | None:
    job_id = raw.get("job_id")
    title = raw.get("title")
    if not job_id or not title:
        return None

    salary_raw = raw.get("salary") or None
    smin, smax = parse_salary(salary_raw or "")

    return JobPosting(
        source=Source.BOSS,
        job_id=str(job_id),
        title=str(title),
        company=str(raw.get("company") or ""),
        salary_raw=salary_raw,
        salary_min_k=smin,
        salary_max_k=smax,
        city=raw.get("city") or None,
        district=raw.get("district") or None,
        experience=raw.get("experience") or None,
        education=raw.get("education") or None,
        skills=[s for s in (raw.get("skills") or []) if s],
        description=raw.get("description") or None,
        url=raw.get("url") or None,
        security_id=raw.get("security_id") or None,
    )


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/health"):
            store = Storage(settings.db_path)
            n = store.count()
            pending = store.count_pending_jd()
            store.close()
            done_at = read_auto_done()
            self._json(
                200,
                {
                    "ok": True,
                    "total": n,
                    "jd_pending": pending,
                    "auto_done": done_at > 0,
                    # 调用方用时间戳判断「是不是本次跑的」，避免上一次的残留标记误判
                    "auto_done_at": done_at,
                },
            )
            return

        if self.path.startswith("/pending"):
            limit = 200
            if "limit=" in self.path:
                try:
                    limit = int(self.path.split("limit=")[1].split("&")[0])
                except Exception:
                    pass
            store = Storage(settings.db_path)
            jobs = store.pending_jd(limit)
            store.close()
            # 详情页需要 securityId 才能正常打开，这里补进 URL
            for j in jobs:
                sid = j.get("security_id")
                if sid:
                    j["url"] = (
                        f"https://www.zhipin.com/job_detail/{j['job_id']}.html"
                        f"?securityId={sid}"
                    )
            self._json(200, {"ok": True, "count": len(jobs), "jobs": jobs})
            return

        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            self._json(400, {"ok": False, "error": f"bad json: {e}"})
            return

        if self.path.startswith("/auto-done"):
            at = mark_auto_done()
            print(f"[auto] 浏览器端报告采集完成 {at:.0f}", flush=True)
            self._json(200, {"ok": True, "at": at})
            return

        if self.path.startswith("/debug"):
            html = data.get("html") or ""
            url = data.get("url") or ""
            p = Path("data/raw/fail_sample.html")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(html, encoding="utf-8")
            print(f"[debug] 失败样本 {len(html)} 字符 <- {url[:80]}", flush=True)
            self._json(200, {"ok": True, "saved": str(p), "bytes": len(html)})
            return

        if self.path.startswith("/jd-fail"):
            ids = data.get("job_ids") or []
            store = Storage(settings.db_path)
            n = store.bump_jd_attempts([str(i) for i in ids if i])
            store.close()
            print(f"[jd-fail] 记录失败 {len(ids)} 条（写入 {n}）", flush=True)
            self._json(200, {"ok": True, "updated": n})
            return

        if self.path.startswith("/jd"):
            items = data.get("items") or []
            store = Storage(settings.db_path)
            written = 0
            for item in items:
                jid = item.get("job_id")
                desc = item.get("description") or ""
                if not jid or not desc:
                    continue
                store.upsert_jd_only(
                    str(jid),
                    desc,
                    title=item.get("title") or "",
                    company=item.get("company") or "",
                    url=item.get("url") or "",
                )
                written += 1
            store.close()
            print(f"[jd] 收到 {len(items)} 条正文，写入 {written} 条", flush=True)
            self._json(200, {"ok": True, "updated": written})
            return

        if not self.path.startswith("/ingest"):
            self._json(404, {"ok": False, "error": "not found"})
            return

        items = data.get("jobs") or []
        store = Storage(settings.db_path)
        new = 0
        for item in items:
            posting = to_posting(item)
            if posting is None:
                continue
            if store.upsert(posting):
                new += 1
        total = store.count()
        store.close()

        print(f"[ingest] 收到 {len(items)} 条，新增 {new} 条，库内共 {total} 条", flush=True)
        self._json(200, {"ok": True, "received": len(items), "new": new, "total": total})

    def log_message(self, fmt: str, *args) -> None:
        return  # 静音默认日志，避免刷屏


def serve(port: int = PORT, host: str = HOST) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"job-scout 接收服务已启动: http://{host}:{port}", flush=True)
    print("  健康检查: GET  /health", flush=True)
    print("  接收数据: POST /ingest  {\"jobs\": [...]}", flush=True)
    print("Ctrl+C 停止", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止", flush=True)
    finally:
        server.server_close()


def start_ingest_in_thread(port: int = PORT, host: str = HOST) -> bool:
    """在后台线程起接收服务（供 API 进程内嵌）。

    端口已被占用时返回 False，调用方应假定外部已有服务。
    """
    import socket
    import threading

    probe = socket.socket()
    try:
        probe.bind((host, port))
    except OSError:
        return False
    finally:
        probe.close()

    threading.Thread(target=serve, args=(port, host), daemon=True).start()
    return True
