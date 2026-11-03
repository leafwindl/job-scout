"""问答接口：普通响应 + SSE 流式。

`use_profile=true` 时会把简历摘要拼进 prompt，用于「我适不适合这类岗位」的提问。
"""

from __future__ import annotations

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from api.app.deps import Pipeline
from api.app.schemas import AskRequest, AskResponse, Citation
from job_scout.profile import build_profile_text, load_profile
from job_scout.rag.generate import stream_ask

router = APIRouter(prefix="/ask", tags=["ask"])


def _profile_text(enabled: bool, max_chars: int = 2500) -> str:
    """取简历摘要；没上传或没开启就返回空串。"""
    if not enabled:
        return ""
    profile = load_profile()
    if profile is None or not profile.has_content:
        return ""
    return build_profile_text(profile)[:max_chars]


@router.post("", response_model=AskResponse)
def ask(req: AskRequest, pipe: Pipeline) -> AskResponse:
    ans = pipe.ask(
        req.question,
        k=req.k,
        profile_text=_profile_text(req.use_profile),
    )
    return AskResponse(
        answer=ans.text,
        mode=ans.mode,
        citations=[Citation(**c) for c in ans.citations],
        docs_count=ans.docs_count,
    )


@router.get("/stream")
def ask_stream(
    q: str,
    pipe: Pipeline,
    k: int = 5,
    use_profile: bool = False,
) -> EventSourceResponse:
    """SSE 事件流：meta → token* → done。

    前端用 EventSource 或 fetch+ReadableStream 消费。
    """
    profile_text = _profile_text(use_profile)

    def event_gen():
        for event, payload in stream_ask(
            q,
            pipe.retriever,
            llm=pipe.llm,
            k=k,
            profile_text=profile_text,
        ):
            yield {"event": event, "data": json.dumps(payload, ensure_ascii=False)}

    return EventSourceResponse(event_gen())
