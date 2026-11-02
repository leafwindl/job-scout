"""检索接口。"""

from __future__ import annotations

from fastapi import APIRouter

from api.app.deps import Pipeline
from api.app.schemas import SearchHit, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(req: SearchRequest, pipe: Pipeline) -> SearchResponse:
    results = pipe.search(req.query, k=req.k)
    hits = [
        SearchHit(
            job_id=d.doc_id,
            title=d.title,
            company=d.company,
            salary=d.meta.get("salary") or "",
            district=d.meta.get("district") or "",
            url=d.meta.get("url") or "",
            score=round(score, 6),
            skills=d.meta.get("skills") or [],
            category=d.meta.get("category") or "",
        )
        for d, score in results
    ]
    return SearchResponse(query=req.query, total=len(hits), hits=hits)
