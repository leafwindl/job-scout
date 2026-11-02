"""公司画像与技术准备接口。

两个接口都支持 `deep` 参数：
- `deep=false`（默认）只算统计，毫秒级返回，用于首屏
- `deep=true` 再调 LLM 做分析，约 20 秒，前端拿到统计后再请求
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from job_scout.company import build_company_profile, list_companies, prep_analysis
from job_scout.profile import load_profile
from job_scout.rag.llm import get_llm

router = APIRouter(tags=["company"])


@router.get("/companies")
def companies(min_jobs: int = 1) -> dict:
    return {"items": list_companies(min_jobs)}


@router.get("/company/{name}")
def company(name: str, deep: bool = False) -> dict:
    llm = get_llm() if deep else None
    data = build_company_profile(name, llm, deep=deep)
    if data.get("error"):
        raise HTTPException(404, data["error"])
    return data


@router.get("/prep")
def prep(deep: bool = False) -> dict:
    profile = load_profile()
    if profile is None or not profile.has_content:
        raise HTTPException(400, "还没有上传简历，先到 /profile 上传 PDF")
    return prep_analysis(profile, get_llm() if deep else None, deep=deep)
