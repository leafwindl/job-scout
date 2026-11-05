"""岗位匹配与打招呼生成接口。"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from job_scout.codebase import (
    CODE_DIR,
    all_contexts,
    list_saved,
    pick_most_relevant_project,
    relevant_code_context,
)
from job_scout.codereact import analyze_for_job
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
from job_scout.textclean import extract_jd_core

router = APIRouter(tags=["match"])


def _get_job(job_id: str) -> sqlite3.Row:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM postings WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(404, "岗位不存在")
    return row


def _jd_text(row: sqlite3.Row, budget: int = 2500) -> str:
    """给 LLM 用的 JD 文本。

    超长 JD（>2000 字）有 LLM 洗过的精简版（jd_clean），优先用它；
    没有就用原文截断——95% 的 JD 本来就短，直接给就行。
    """
    keys = row.keys() if hasattr(row, "keys") else []
    if "jd_clean" in keys:
        clean = row["jd_clean"]
        if clean and len(clean) > 50:
            return clean[:budget]
    return (row["description"] or "")[:budget]


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
    # 前端如果已经跑过「简历建议」，把结果传过来，省一次 20 秒的 LLM 调用
    rewrite: dict | None = Field(default=None, description="已有的简历改写建议")


@router.post("/match/{job_id}")
def match(job_id: str) -> dict:
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(job_id)

    result = match_job(
        profile,
        row["title"] or "",
        row["company"] or "",
        _jd_text(row),
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
    """针对岗位给出简历改写建议。

    流程：
    1. 按 JD 选出最相关的那个项目（词频打分，秒级）
    2. 对这个项目跑 ReAct 读代码（12 轮，约 45 秒），直接产出改写建议
    3. 其余项目用静态技术画像兜底

    `project` 指定项目名时强制用它，跳过第 1 步。
    """
    profile = _require_profile()
    llm = _require_llm()
    row = _get_job(job_id)

    resume_names = [(x.get("name") or "").strip() for x in profile.projects]
    jd = _jd_text(row)
    jd_core = extract_jd_core(jd, 900)

    # 1) 选项目
    if project:
        best = next((it for it in list_saved() if it["project_name"] == project), None)
        if best:
            full = CODE_DIR / f"{best['slug']}.json"
            if full.exists():
                best = {**best, **json.loads(full.read_text(encoding="utf-8"))}
    else:
        best = pick_most_relevant_project(jd, resume_names)

    # 2) 对该项目跑 ReAct，直接产出「与岗位相关的实现 + 简历该怎么改」
    react_text = ""
    react_meta: dict = {}
    used_project = ""
    if best and best.get("path") and best.get("tree") and llm is not None:
        used_project = best["project_name"]
        proj_desc = _project_desc(profile, used_project)
        react = analyze_for_job(
            best["path"],
            used_project,
            best.get("tree") or [],
            jd_core,
            proj_desc,
            llm,
            max_turns=12,
        )
        react_text = react.text if not react.error else ""
        react_meta = {
            "project": used_project,
            "turns": react.turns,
            "tool_calls": react.tool_calls,
            "files_read": react.files_read,
            "elapsed": round(react.elapsed, 1),
            "error": react.error,
        }

    # 3) 其余项目用静态画像
    rest_ctx = all_contexts(max_chars=1500, only_projects=resume_names)
    code_ctx = (react_text + "\n\n" + rest_ctx).strip() if react_text else rest_ctx

    result = rewrite_resume(
        profile,
        row["title"] or "",
        row["company"] or "",
        jd,
        llm,
        code_context=code_ctx,
    )
    return {
        "job_id": job_id,
        "title": row["title"],
        "company": row["company"],
        "used_code": bool(code_ctx),
        "react": react_meta,
        **result,
    }


def _project_desc(profile, name: str) -> str:
    """取简历里某个项目的原文描述，给 ReAct 当对照。"""
    for p in profile.projects:
        pname = (p.get("name") or "").strip()
        if pname == name or (pname and (pname in name or name in pname)):
            bullets = "\n".join(f"- {b}" for b in (p.get("bullets") or []))
            return f"{pname}\n{bullets}".strip()
    return ""


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
                  _jd_text(row), llm)

    # 简历改写建议：前端已经跑过就复用（省 20 秒），没跑才现算
    reuse = bool(req.rewrite)
    if reuse:
        brief = build_rewrite_brief(req.rewrite or {})
    else:
        resume_names = [(x.get("name") or "").strip() for x in profile.projects]
        code_ctx = relevant_code_context(
            _jd_text(row),
            only_projects=resume_names,
            max_chars=2000,
        )
        rw = rewrite_resume(
            profile,
            row["title"] or "",
            row["company"] or "",
            _jd_text(row),
            llm,
            code_context=code_ctx,
        )
        brief = build_rewrite_brief(rw)

    text = generate_greeting(
        profile,
        row["title"] or "",
        row["company"] or "",
        _jd_text(row),
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
        "used_brief": len(brief) > 20,
        "reused_rewrite": reuse,
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
        _jd_text(row),
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
