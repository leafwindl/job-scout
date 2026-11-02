"""依赖注入：RAG 流水线单例。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from job_scout.rag.pipeline import RagPipeline, get_pipeline


def pipeline_dep() -> RagPipeline:
    return get_pipeline()


Pipeline = Annotated[RagPipeline, Depends(pipeline_dep)]
