"""临时岗位分析：不依赖采集数据库。

用途是浏览器悬浮窗——用户在 BOSS 上随便点开一个岗位，
脚本把标题/公司/JD 文本发过来，立刻返回匹配度和缺口，
以及针对这条 JD 的问答。

这些岗位没有入库，所以不能用 job_id 走 /match。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from job_scout.profile import (
    build_profile_text,
    load_profile,
    match_job,
)
from job_scout.rag.llm import get_llm

router = APIRouter(prefix="/analyze", tags=["analyze"])

MAX_JD = 4000


class AnalyzeRequest(BaseModel):
    title: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=100)
    jd: str = Field(min_length=20, max_length=20000)
    city: str = Field(default="", max_length=50)
    salary: str = Field(default="", max_length=50)


class AskRequest(BaseModel):
    jd: str = Field(min_length=20, max_length=20000)
    question: str = Field(min_length=1, max_length=300)


def _require_profile():
    profile = load_profile()
    if profile is None or not profile.has_content:
        raise HTTPException(400, "还没有上传简历，先到 /profile 上传 PDF")
    return profile


def _require_llm():
    llm = get_llm()
    if llm is None:
        raise HTTPException(400, "没配置模型 Key，无法分析")
    return llm


@router.post("")
def analyze(req: AnalyzeRequest) -> dict:
    """对一条临时 JD 打匹配分（不入库）。"""
    profile = _require_profile()
    llm = _require_llm()

    result = match_job(profile, req.title, req.company, req.jd, llm)
    return {
        "title": req.title,
        "company": req.company,
        "city": req.city,
        "salary": req.salary,
        **result,
    }


ASK_PROMPT = """你在帮求职者快速判断一个岗位。下面是岗位信息和他自己的简历。

【我的简历】
{profile}

【岗位】
{title} ｜ {company}
JD：
{jd}

【问题】
{question}

规则：
- 只依据上面给的信息回答，不要引入外部猜测
- 涉及「我合不合适」时，对照简历里**具体项目或技能**说，不要泛泛而谈
- 简历里没有的能力，明确说没有
- 回答控制在 3-5 句话，直接给结论，别铺垫
"""


@router.post("/ask")
def ask(req: AskRequest) -> dict:
    """针对一条临时 JD 提问（不入库）。"""
    profile = _require_profile()
    llm = _require_llm()

    prompt = ASK_PROMPT.format(
        profile=build_profile_text(profile, compact=True),
        title="",
        company="",
        jd=req.jd[:MAX_JD],
        question=req.question,
    )
    try:
        answer = llm.complete("你是一个务实的求职顾问。", prompt, temperature=0.2)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"生成失败：{type(e).__name__}") from e

    return {"answer": answer.strip(), "question": req.question}
