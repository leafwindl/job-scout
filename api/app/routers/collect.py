"""采集触发与进度。

设计参考：
- Crawlab 的任务状态机：idle / running / done / stalled（显式状态，不用布尔）
- Mercure 的异步任务模式：前端发起、后台执行、前端轮询收进度
  （低频更新用轮询就够，不必上 SSE）
"""

from __future__ import annotations

import time
from urllib.parse import quote

from fastapi import APIRouter
from pydantic import BaseModel, Field

from job_scout.config import settings
from job_scout.constants import BOSS_SEARCH_URL, CITY_CODES
from job_scout.server import read_auto_done
from job_scout.storage import Storage

router = APIRouter(prefix="/collect", tags=["collect"])

# 单用户场景：只记最近一次采集任务
_LAST: dict = {"started_at": 0.0, "keyword": "", "city": "", "url": ""}
# 最近几次采样，用来判断「还有没有进展」
_SAMPLES: list[tuple[float, int, int]] = []

TIMEOUT_SEC = 40 * 60


class StartRequest(BaseModel):
    keyword: str = Field(default="Agent 实习", max_length=50)
    city: str = Field(default="广州", max_length=20)


class StartResponse(BaseModel):
    url: str
    started_at: float
    city_code: str
    keyword: str
    city: str


class StatusResponse(BaseModel):
    state: str  # idle / running / done / stalled
    total: int
    with_jd: int
    jd_pending: int
    elapsed: int
    done_at: float
    message: str


@router.post("/start", response_model=StartResponse)
def start(req: StartRequest) -> StartResponse:
    code = CITY_CODES.get(req.city) or CITY_CODES["广州"]
    url = f"{BOSS_SEARCH_URL}?query={quote(req.keyword)}&city={code}&jobscout=auto"
    now = time.time()
    _LAST.update({"started_at": now, "keyword": req.keyword, "city": req.city, "url": url})
    _SAMPLES.clear()
    return StartResponse(
        url=url,
        started_at=now,
        city_code=code,
        keyword=req.keyword,
        city=req.city,
    )


@router.get("/status", response_model=StatusResponse)
def status() -> StatusResponse:
    store = Storage(settings.db_path)
    total = store.count()
    pending = store.count_pending_jd()
    store.close()
    with_jd = total - pending

    started = float(_LAST.get("started_at") or 0)
    done_at = read_auto_done()
    now = time.time()
    elapsed = int(now - started) if started else 0

    if not started:
        state, msg = "idle", "还没有发起采集"
    elif done_at >= started:
        state, msg = "done", f"采集完成：库内 {total} 条，{with_jd} 条有 JD"
    elif elapsed > TIMEOUT_SEC:
        state, msg = "stalled", "超过 40 分钟未完成，可能被风控或未登录"
    else:
        _SAMPLES.append((now, total, pending))
        while len(_SAMPLES) > 6:
            _SAMPLES.pop(0)

        if len(_SAMPLES) >= 5:
            first, last = _SAMPLES[0], _SAMPLES[-1]
            moved = last[1] != first[1] or last[2] != first[2]
            if moved:
                state, msg = "running", "正在采集"
            else:
                state, msg = "stalled", "最近没有新增，等待脚本回报完成…"
        else:
            state, msg = "running", "正在采集"

    return StatusResponse(
        state=state,
        total=total,
        with_jd=with_jd,
        jd_pending=pending,
        elapsed=elapsed,
        done_at=done_at,
        message=msg,
    )


@router.post("/reset")
def reset() -> dict:
    """清空本次任务状态（不影响库里的数据）。"""
    _LAST.update({"started_at": 0.0, "keyword": "", "city": "", "url": ""})
    _SAMPLES.clear()
    return {"ok": True}
