"""问答接口：普通响应 + SSE 流式。"""

from __future__ import annotations

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from api.app.deps import Pipeline
from api.app.schemas import AskRequest, AskResponse, Citation
from job_scout.rag.generate import stream_ask

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
def ask(req: AskRequest, pipe: Pipeline) -> AskResponse:
    ans = pipe.ask(req.question, k=req.k)
    return AskResponse(
        answer=ans.text,
        mode=ans.mode,
        citations=[Citation(**c) for c in ans.citations],
        docs_count=ans.docs_count,
    )


@router.get("/stream")
def ask_stream(q: str, pipe: Pipeline, k: int = 5) -> EventSourceResponse:
    """SSE 事件流：meta → token* → done。

    前端用 EventSource 或 fetch+ReadableStream 消费。
    """

    def event_gen():
        for event, payload in stream_ask(q, pipe.retriever, llm=pipe.llm, k=k):
            yield {"event": event, "data": json.dumps(payload, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
