"""公司画像与技术准备。

P2：从同一家公司的多条 JD 里，挖「技术/项目倾向」这种隐含信息——
    关键词只告诉你「要 Python」，画像告诉你「这家公司在做什么、喜欢什么样的人」。
P3：把岗位要求聚合成「你缺什么、先补什么」。
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter

from job_scout.config import settings
from job_scout.profile import Profile, build_profile_text

# 行为信号词：用来刻画一家公司的风格
SIGNALS: dict[str, list[str]] = {
    "从 0 到 1": ["0到1", "从零", "搭建", "建设", "从无到有", "0-1"],
    "贴近业务": ["业务", "场景", "需求方", "客户", "落地", "甲方"],
    "工程化": ["工程", "架构", "性能", "部署", "上线", "高并发", "稳定性"],
    "算法研究": ["论文", "顶会", "发表", "研究", "benchmark", "实验"],
    "开源": ["开源", "github", "社区", "贡献", "pr "],
    "产品思维": ["产品", "用户体验", "需求分析", "原型", "交互"],
    "数据驱动": ["数据", "指标", "ab test", "实验设计", "分析", "归因"],
    "团队协作": ["团队", "协作", "沟通", "跨部门", "配合"],
}

COMPANY_PROMPT = """你在帮求职者评估一家公司。

【公司】{company}
【岗位数】{count}（均为 AI/Agent 相关实习岗）
【地区】{districts}
【薪资】{salary}
【Top 技能】{skills}
【JD 行为信号（每条 JD 平均命中次数）】{signals}
【岗位样本】
{samples}

请输出 JSON（不要解释、不要 markdown）：
{{
  "business": "这家公司大概在做什么（一句话，基于 JD 推断，不确定就说不确定）",
  "tech_style": "技术风格（一两句话）：偏工程/偏算法/偏业务/全栈",
  "team": "团队特征：规模感、节奏、协作方式（基于 JD 措辞推断）",
  "person_fit": "什么样背景的人在这里更吃香",
  "interview_focus": ["面试大概会问什么，2-3 条"],
  "verdict": "值得投 / 一般 / 慎重，并给一句理由"
}}

规则：
- 只基于给出的 JD 推断，不要编造公司业务事实
- 如果岗位数太少（<2），在 business 里说明推断依据不足
- 不要复述岗位名
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def list_companies(min_jobs: int = 1) -> list[dict]:
    """列出有岗位的公司（按岗位数排序）。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT company, COUNT(*) AS n, "
        "  GROUP_CONCAT(DISTINCT district) AS districts "
        "FROM postings WHERE is_active = 1 AND is_relevant = 1 "
        "GROUP BY company HAVING n >= ? ORDER BY n DESC, company",
        (min_jobs,),
    ).fetchall()
    conn.close()
    return [
        {
            "company": r["company"],
            "jobs": r["n"],
            "districts": [d for d in (r["districts"] or "").split(",") if d],
        }
        for r in rows
    ]


def company_jobs(company: str) -> list[sqlite3.Row]:
    conn = _conn()
    rows = conn.execute(
        "SELECT job_id, title, salary_raw, district, skills, description FROM postings "
        "WHERE company = ? AND is_active = 1 AND is_relevant = 1 "
        "ORDER BY last_seen DESC",
        (company,),
    ).fetchall()
    conn.close()
    return rows


def _signal_scores(jobs: list[sqlite3.Row]) -> dict[str, float]:
    """每条 JD 平均命中次数，避免「岗位多的公司分虚高」。"""
    text = " ".join((j["description"] or "") for j in jobs).lower()
    n = max(1, len(jobs))
    out = {}
    for name, words in SIGNALS.items():
        hits = sum(text.count(w) for w in words)
        out[name] = round(hits / n, 2)
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def _skill_counts(jobs: list[sqlite3.Row]) -> list[tuple[str, int]]:
    cnt: Counter[str] = Counter()
    for j in jobs:
        raw = (j["skills"] or "").strip()
        try:
            items = json.loads(raw) if raw else []
        except Exception:
            items = [x.strip(' "[]') for x in raw.split(",")]
        for s in items:
            s = str(s).strip().strip('"')
            if s:
                cnt[s] += 1
    return cnt.most_common(12)


def build_company_profile(company: str, llm, deep: bool = True) -> dict:
    """deep=False 只算统计（毫秒级），deep=True 再加 LLM 分析（约 20 秒）。"""
    jobs = company_jobs(company)
    if not jobs:
        return {"error": "没有这家公司的在架岗位"}

    districts = sorted({(j["district"] or "") for j in jobs if j["district"]})
    salaries = [j["salary_raw"] for j in jobs if j["salary_raw"]]
    skills = _skill_counts(jobs)
    signals = _signal_scores(jobs)

    samples = "\n".join(
        f"- {j['title']}（{(j['description'] or '')[:160]}…）" for j in jobs[:6]
    )

    result = {
        "company": company,
        "job_count": len(jobs),
        "districts": districts,
        "salary": salaries[0] if salaries else "未标注",
        "skills": [{"name": s, "count": c} for s, c in skills],
        "signals": signals,
        "jobs": [
            {"job_id": j["job_id"], "title": j["title"], "salary": j["salary_raw"]}
            for j in jobs[:20]
        ],
    }

    if not deep or llm is None:
        return result

    prompt = COMPANY_PROMPT.format(
        company=company,
        count=len(jobs),
        districts="、".join(districts) or "未知",
        salary="、".join(sorted(set(salaries))[:4]) or "未标注",
        skills="、".join(f"{s}({c})" for s, c in skills[:8]) or "未标注",
        signals="、".join(f"{k}:{v}" for k, v in list(signals.items())[:5]),
        samples=samples or "无",
    )
    try:
        raw = llm.complete("你是一个严谨的公司分析顾问。", prompt, temperature=0.3)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group()) if m else {}
    except Exception as e:  # noqa: BLE001
        data = {"error": f"{type(e).__name__}: {e}"}

    result.update(
        {
            "business": data.get("business", ""),
            "tech_style": data.get("tech_style", ""),
            "team": data.get("team", ""),
            "person_fit": data.get("person_fit", ""),
            "interview_focus": data.get("interview_focus") or [],
            "verdict": data.get("verdict", ""),
        }
    )
    return result


# ---------------------------------------------------------------- P3 技术准备

PREP_PROMPT = """你在帮求职者做「技术准备计划」。

【我的技能】
{have}

【目标岗位范围】
{scope}

【高频要求（出现该要求的岗位数 / 总岗位数）】
{demand}

【我明确缺的】
{missing}

输出 JSON（不要解释、不要 markdown）：
{{
  "overview": "两句话：整体差距在哪，先补什么最划算",
  "learn": [
    {{"skill": "要补的技术", "why": "为什么优先补（关联多少岗位）", "how": "具体怎么学/怎么证明会（1-2 句，要可执行）"}}
  ],
  "leverage": ["我已经会、但没在简历里讲清楚的点，讲清楚就能加分"],
  "skip": ["不值得花时间补的（岗位少或与目标方向不符）"]
}}

规则：
- learn 只列 3-5 项，按性价比排序
- how 要具体：看什么文档、写什么 demo、在哪个项目里加什么
- 禁止建议去「刷 leetcode 200 题」这种空话
"""


def prep_analysis(profile: Profile, llm, limit_jobs: int = 200, deep: bool = True) -> dict:
    """deep=False 只做技能差集（毫秒级），deep=True 再加 LLM 学习计划（约 20 秒）。"""
    conn = _conn()
    rows = conn.execute(
        "SELECT title, skills, description FROM postings "
        "WHERE is_active = 1 AND is_relevant = 1 "
        "ORDER BY last_seen DESC LIMIT ?",
        (limit_jobs,),
    ).fetchall()
    conn.close()

    total = max(1, len(rows))

    # 技能栏命中的频次
    demand: Counter[str] = Counter()
    for r in rows:
        raw = (r["skills"] or "").strip()
        try:
            items = json.loads(raw) if raw else []
        except Exception:
            items = [x.strip(' "[]') for x in raw.split(",")]
        for s in items:
            s = str(s).strip().strip('"')
            if s:
                demand[s] += 1

    have_low = {s.lower() for s in (profile.skills or [])}
    have_joined = " ".join(have_low)

    def has(skill: str) -> bool:
        s = skill.lower()
        if s in have_low:
            return True
        # 宽松匹配：FastAPI / fastapi；LangGraph / langgraph
        return len(s) > 2 and s in have_joined

    missing = [(s, c) for s, c in demand.most_common(30) if not has(s)]
    have_signals = [s for s, _ in demand.most_common(30) if has(s)]

    result = {
        "scope": f"{len(rows)} 个在架岗位",
        "demand": [{"skill": s, "jobs": c, "ratio": round(c / total, 2)} for s, c in demand.most_common(20)],
        "have": have_signals[:20],
        "missing": [{"skill": s, "jobs": c} for s, c in missing[:12]],
    }

    if not deep or llm is None:
        return result

    prompt = PREP_PROMPT.format(
        have=build_profile_text(profile)[:2500],
        scope=f"{len(rows)} 个 AI/Agent 实习岗",
        demand="、".join(f"{s}({c}/{total})" for s, c in demand.most_common(15)),
        missing="、".join(f"{s}({c}个岗位)" for s, c in missing[:8]) or "无明显缺口",
    )
    try:
        raw = llm.complete("你是一个务实的求职教练。", prompt, temperature=0.3)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group()) if m else {}
    except Exception as e:  # noqa: BLE001
        data = {"error": f"{type(e).__name__}: {e}"}

    result.update(
        {
            "overview": data.get("overview", ""),
            "learn": data.get("learn") or [],
            "leverage": data.get("leverage") or [],
            "skip": data.get("skip") or [],
        }
    )
    return result
