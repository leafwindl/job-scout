"""岗位匹配与打招呼生成接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from job_scout.codebase import all_contexts, get_context, relevant_code_context
from job_scout.config import settings
from job_scout.profile import (
    build_rewrite_brief,
    generate_greeting,
    load_profile,
    match_job,
    revise_greeting,
    rewrite_resume,
)
from job_scout.rag.llm import get_llm

router = APIRouter(tags=["match"])


def _get_job(job_id: str) -> sqlite3.Row:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM postings WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(404, "岗位不存在")
    return row


def _require_profile():
    p = load_profile()
    if p is None or not p.has_content:
        raise HTTPException(400, "还没有上传简历，先到 /profile 上传 PDF")
    return p


def _require_llm():
    llm = get_llm()
    if llm is None:
        raise HTTPException(503, "没有配置模型 Key，无法评估")
    return llm


class GreetRequest(BaseModel):
    job_id: str
    extra: str = Field(default="", max_length=200, description="额外要求，比如突出某个项目")


@router.post("/match/{job_id}")
def match(job_id: str) -> dict:
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(job_id)

    result = match_job(
        profile,
        row["title"] or "",
        row["company"] or "",
        row["description"] or "",
        llm,
    )
    return {
        "job_id": job_id,
        "title": row["title"],
        "company": row["company"],
        **result,
    }


@router.post("/resume/rewrite/{job_id}")
def rewrite(job_id: str, project: str = "") -> dict:
    """针对岗位给出简历改写建议（只调整表达，不编造经历）。

    `project` 指定简历里的项目名时，会带上该项目的代码摘要，
    让建议能引用代码里确实有的技术点。
    """
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(job_id)

    # 指定项目就只取那个；没指定就用简历里有的项目代码
    resume_names = [(x.get("name") or "").strip() for x in profile.projects]
    code_ctx = (
        get_context(project) if project else all_contexts(only_projects=resume_names)
    )

    result = rewrite_resume(
        profile,
        row["title"] or "",
        row["company"] or "",
        row["description"] or "",
        llm,
        code_context=code_ctx,
    )
    return {
        "job_id": job_id,
        "title": row["title"],
        "company": row["company"],
        "used_code": bool(code_ctx),
        **result,
    }


@router.post("/greet")
def greet(req: GreetRequest) -> dict:
    """生成打招呼消息。

    按用户要求简化输入：JD 的职责/要求段 + 简历改写建议 + 简历摘要。
    简历建议针对这个岗位调过措辞，比简历原文更贴。
    """
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(req.job_id)

    # 先算匹配度：既给招呼语提供可强调的点，也返回给前端
    m = match_job(profile, row["title"] or "", row["company"] or "",
                  row["description"] or "", llm)

    # 简历改写建议：针对这个岗位，措辞已经调过，拿来写招呼语最贴
    resume_names = [(x.get("name") or "").strip() for x in profile.projects]
    code_ctx = relevant_code_context(
        row["description"] or "",
        only_projects=resume_names,
        max_chars=2000,
    )
    rw = rewrite_resume(
        profile,
        row["title"] or "",
        row["company"] or "",
        row["description"] or "",
        llm,
        code_context=code_ctx,
    )
    brief = build_rewrite_brief(rw)

    text = generate_greeting(
        profile,
        row["title"] or "",
        row["company"] or "",
        row["description"] or "",
        llm,
        extra=req.extra,
        rewrite_brief=brief,
    )
    return {
        "job_id": req.job_id,
        "title": row["title"],
        "company": row["company"],
        "greeting": text,
        "chars": len(text),
        "used_code": bool(code_ctx),
        "used_brief": len(brief) > 20,
        "match": m,
    }


class ReviseGreetRequest(BaseModel):
    job_id: str
    # 上一版招呼语
    current: str = Field(min_length=1, max_length=2000)
    # 求职者的修改要求，比如「太长了」「别提薪资」「强调 RAG 项目」
    feedback: str = Field(min_length=1, max_length=500)


@router.post("/greet/revise")
def revise_greet(req: ReviseGreetRequest) -> dict:
    """按用户反馈重写招呼语。"""
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(req.job_id)

    text = revise_greeting(
        profile,
        row["title"] or "",
        row["company"] or "",
        row["description"] or "",
        req.current,
        req.feedback,
        llm,
    )

    return {
        "job_id": req.job_id,
        "greeting": text,
        "chars": len(text),
        "feedback": req.feedback,
    }
