"""job-scout API 入口。

启动：
    uv run uvicorn api.app.main:app --reload --port 8001
文档：
    http://127.0.0.1:8001/docs

同一个进程里还会起 8765 的采集接收服务，
这样网页端发起采集时油猴脚本有地方推数据，不需要另外开终端。
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.app.routers import ask, collect, company, jobs, match, profile, search
from job_scout.rag.pipeline import get_pipeline
from job_scout.server import PORT as COLLECT_PORT
from job_scout.server import start_ingest_in_thread


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 容器里必须绑 0.0.0.0 才能被宿主的浏览器访问
    host = os.getenv("COLLECT_HOST", "127.0.0.1")
    started = start_ingest_in_thread(COLLECT_PORT, host)
    if started:
        print(f"[collect] 采集接收服务已随 API 启动 {host}:{COLLECT_PORT}", flush=True)
    else:
        print(f"[collect] {host}:{COLLECT_PORT} 已被占用，复用已有服务", flush=True)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="job-scout API",
    version="0.1.0",
    description="岗位情报 RAG：检索、问答、岗位库、采集",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)
app.include_router(ask.router)
app.include_router(jobs.router)
app.include_router(collect.router)
app.include_router(profile.router)
app.include_router(match.router)
app.include_router(company.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    pipe = get_pipeline()
    return {
        "ok": True,
        "docs": len(pipe.docs),
        "has_llm": pipe.has_llm,
        "mode": "llm" if pipe.has_llm else "extractive",
    }
