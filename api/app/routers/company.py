"""公司画像与技术准备接口。"""

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
def company(name: str) -> dict:
    llm = get_llm()
    data = build_company_profile(name, llm)
    if data.get("error"):
        raise HTTPException(404, data["error"])
    return data


@router.get("/prep")
def prep() -> dict:
    profile = load_profile()
    if profile is None or not profile.has_content:
        raise HTTPException(400, "还没有上传简历，先到 /profile 上传 PDF")
    return prep_analysis(profile, get_llm())
