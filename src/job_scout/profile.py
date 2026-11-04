"""我的画像：从简历 PDF 里提取结构化能力信息。

设计取舍：
- **不做整篇重写**，只提取事实（教育/项目/技能/经历），保住真实性
- 结构化成 JSON 后，匹配、打招呼、简历改写都基于同一份数据
- 提取失败时保留原文，至少还能被问答用上
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

PROFILE_PATH = Path("data/profile.json")
RESUME_DIR = Path("data/resume")

EXTRACT_PROMPT = """你是一个简历解析器。从给定的简历文本中提取结构化信息。

只输出 JSON，不要任何解释、不要 markdown 代码块：
{
  "name": "姓名，没有留空",
  "target": "求职意向/目标岗位，没有留空",
  "education": [{"school": "", "major": "", "degree": "", "time": ""}],
  "skills": ["按重要程度排列的技术栈/工具，用原文措辞"],
  "projects": [
    {"name": "", "period": "", "tech": [], "summary": "", "bullets": ["原文的工作内容条目"]}
  ],
  "experience": [{"company": "", "role": "", "period": "", "bullets": []}]
}

**最重要的规则：bullets 必须逐条照搬原文，禁止概括。**

- 原文「工作内容」有 N 条，bullets 就要有 N 条，顺序保持一致
- **保留全部数字**：百分比、MRR/Recall 等指标、耗时、条数、人数、页面数、提升幅度
- **保留原文的动词和限定词**：「设计并实现」「使…从…提升到…」「因…而关闭」
- 一条 bullet 可以长，宁可长也不要压成一句话
- 不许把两条合成一条，不许把「具体做了什么」换成「实现了某系统」这种空话

其他规则：
- 原文的「简述 / 项目简介」放进 summary 字段（这一条可以概括）
- 只提取原文出现过的信息，禁止编造；原文没有的字段留空字符串或空数组
- skills 只要技术名词，不要把「沟通能力强」这类软素质放进去
- 日期缺失就留空，不要猜
"""


@dataclass
class Profile:
    name: str = ""
    target: str = ""
    education: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    raw_text: str = ""
    source_file: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> Profile:
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    @property
    def has_content(self) -> bool:
        return bool(self.skills or self.projects or self.experience)


def extract_pdf_text(path: Path) -> str:
    """从 PDF 里抽文本。简历一般是导出 PDF，文本层完整。"""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages).strip()


def parse_profile(text: str, llm) -> Profile:
    """用 LLM 把简历文本转成结构化画像。失败时退化为只保留原文。"""
    if not text.strip():
        return Profile(raw_text="")

    try:
        raw = llm.complete(EXTRACT_PROMPT, text[:8000], temperature=0.0)
    except Exception:
        return Profile(raw_text=text)

    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return Profile(raw_text=text)

    try:
        data = json.loads(m.group())
    except Exception:
        return Profile(raw_text=text)

    data.setdefault("raw_text", text)
    return Profile.from_dict(data)


def save_profile(p: Profile, db_path: Path = Path("data/job_scout.db")) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(
        json.dumps(p.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_profile() -> Profile | None:
    if not PROFILE_PATH.exists():
        return None
    try:
        return Profile.from_dict(json.loads(PROFILE_PATH.read_text(encoding="utf-8")))
    except Exception:
        return None


def save_resume_pdf(filename: str, content: bytes) -> Path:
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]", "_", filename) or "resume.pdf"
    path = RESUME_DIR / safe
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------- 匹配

MATCH_PROMPT = """你在帮求职者判断「这个岗位值不值得投」。

【我的能力】
{profile}

【岗位】
标题：{title}
公司：{company}
要求（JD 原文，可能很长）：
{jd}

请输出 JSON（不要解释、不要 markdown）：
{{
  "score": 0-100 的整数，综合匹配度,
  "verdict": "强推 / 可投 / 观望 / 不建议",
  "matched": ["JD 里有、我也具备的点，每条一句话"],
  "missing": ["JD 明确要、但我简历里没有的点，每条一句话"],
  "reason": "两句话内说明为什么是这个分数"
}}

评分参考：
- 80+ 硬技能基本对齐，只差一两个软性要求
- 60-79 主要技能对上，但缺关键项（比如没做过 RAG 却要求 RAG）
- 40-59 方向沾边，能力差距明显
- <40 方向不对或门槛差太远
"""


def build_profile_text(p: Profile, compact: bool = False) -> str:
    """把画像压成给 LLM 看的短文本（省 token）。

    compact=True 用于问答：每个项目只留 1 条要点、截断到 80 字，
    否则 1200 多字的摘要会把首 token 拖到 20 秒。
    """
    parts = []
    if p.target:
        parts.append(f"求职意向：{p.target}")
    if p.skills:
        skills = p.skills[:12] if compact else p.skills[:30]
        parts.append("技能：" + "、".join(skills))

    max_proj = 3 if compact else 5
    max_bullets = 1 if compact else 3
    bullet_len = 80 if compact else 10_000
    for proj in p.projects[:max_proj]:
        bullets = "；".join(
            b[:bullet_len] for b in (proj.get("bullets") or [])[:max_bullets]
        )
        parts.append(
            f"项目：{proj.get('name', '')}"
            f"{'｜' + '、'.join(proj.get('tech') or []) if proj.get('tech') else ''}"
            f"{'｜' + bullets if bullets else ''}"
        )

    for exp in p.experience[: (1 if compact else 3)]:
        bullets = "；".join((exp.get("bullets") or [])[:max_bullets])
        parts.append(
            f"经历：{exp.get('company', '')} {exp.get('role', '')}"
            f"{'｜' + bullets if bullets else ''}"
        )
    if p.education:
        edu = p.education[0]
        parts.append(
            f"教育：{edu.get('school', '')} {edu.get('major', '')} {edu.get('degree', '')}"
        )
    return "\n".join(parts) or p.raw_text[:2000]


VERDICT_ORDER = {"强推": 0, "可投": 1, "观望": 2, "不建议": 3}


GREET_PROMPT = """你在帮求职者写 BOSS 直聘的打招呼消息。

【我的简历】
{profile}

【目标岗位】
{title} ｜ {company}
JD 摘录：
{jd}

要求：
1. **总共 200 字以内，这是硬性要求**——超了 HR 看不完，也算不合格
2. 第一句：我是谁 + 为什么投这个岗，必须扣住 JD 里的**某个具体要求**，不要泛泛说"对贵司感兴趣"
3. 中间：用 1-2 个具体事实证明能力，带上项目名或数字，从简历里来
4. 最后：表达可实习时间和意愿，一句话
5. 禁止编造简历里没有的经历
6. 禁止"贵公司""您好，我是 XX 大学 XX 专业"这类模板腔
7. 直接输出消息正文，不要任何前后缀、不要引号

额外要求：{extra}
"""


REWRITE_PROMPT = """你在帮求职者针对一个具体岗位**改写简历**（不是重写，是调整表达）。

【现有简历】
{profile}

【目标岗位】
{title} ｜ {company}
JD：
{jd}

【项目代码摘要】（自动扫描的项目实况，可能为空）
{code}

输出 JSON（不要解释、不要 markdown）：
{{
  "summary": "一句话：这份简历投这个岗最大的问题是什么",
  "reorder": ["项目名，按投这个岗的建议顺序排列"],
  "rewrites": [
    {{"project": "项目名", "original": "原文某句（可截取）", "suggested": "改写后", "why": "为什么这么改"}}
  ],
  "add": ["建议补充的信息，比如某个技术点、某个量化数字"],
  "cut": ["建议弱化或删掉的内容"]
}}

规则：
- **禁止编造经历**，只能调整已有内容的顺序、措辞、详略
- rewrites 给 2-4 条，挑最影响这个岗位的
- 改写要贴 JD 的用词（JD 说"混合检索"，就别只写"检索"）
- 如果某个项目与岗位无关，直接建议弱化

**如果给了项目代码摘要**：
- 可以用摘要里**事实性**的内容补充简历（用了什么依赖、有几个接口、代码规模、模块划分）
- 例如摘要写"依赖 langgraph、fastapi"，简历没提 LangGraph，就可以建议补上
- 但只能引用摘要里明确出现的内容，**不许推测没写的东西**
- 补进简历的话要像人写的，别把"144 个文件、15868 行"直接抄进去

额外要求：{extra}
"""


def rewrite_resume(
    profile: Profile,
    title: str,
    company: str,
    jd: str,
    llm,
    extra: str = "",
    max_jd: int = 2000,
    code_context: str = "",
) -> dict:
    """针对岗位生成简历改写建议（不编造，只调整表达）。

    code_context 非空时，会把项目代码摘要一起给模型，
    用来补充简历里没写、但代码里确实有的技术点。
    """
    prompt = REWRITE_PROMPT.format(
        profile=build_profile_text(profile) + "\n\n" + (profile.raw_text[:3000] or ""),
        title=title,
        company=company,
        jd=(jd or "")[:max_jd],
        code=(code_context or "")[:3500] or "（未提供项目代码）",
        extra=extra or "无",
    )
    try:
        raw = llm.complete("你是一个务实的简历顾问，只基于事实提建议。", prompt, temperature=0.3)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group()) if m else {}
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}", "summary": "生成失败"}

    return {
        "summary": data.get("summary") or "",
        "reorder": data.get("reorder") or [],
        "rewrites": data.get("rewrites") or [],
        "add": data.get("add") or [],
        "cut": data.get("cut") or [],
    }


REVIEW_PROMPT = """你在审查简历里的一个项目描述，对照的是这个项目的**真实代码**。

【简历里的项目描述】
{resume_project}

【项目代码实际情况】
{code}

输出 JSON（不要解释、不要 markdown）：
{{
  "verdict": "一句话总体判断：这段描述和代码的差距在哪",
  "inaccurate": [
    {{"claim": "简历里写的", "reality": "代码里的实际情况", "fix": "建议改成"}}
  ],
  "missing": [
    {{"fact": "代码里有、但简历没写的", "suggest": "可以补进简历的说法"}}
  ],
  "rewrites": [
    {{"original": "原文某句", "suggested": "改写后", "why": "依据代码的哪部分"}}
  ],
  "cut": ["建议删掉或弱化的说法"]
}}

规则：
- **只依据代码摘要判断**，摘要里没提到的东西不要说「代码里没有」
- inaccurate 最多 3 条：挑真的会让人怀疑的夸大表述
- missing 挑 2-4 条**最有说服力**的事实（技术栈、接口数量、模块划分、规模）
- 改写要像人写的，别把「146 个文件、16171 行」直接抄进去
- 如果代码和描述基本对得上，inaccurate 可以空，只给 missing 和 rewrites
- 中文，简洁
"""


def _find_project(profile: Profile, project_name: str) -> dict:
    """按名字找简历里的项目。

    匹配顺序：完全相同 -> 互相包含 -> 模糊相似度（应对「AI 求职助手」vs「Echo AI 助手」这种改名）。
    """
    if not project_name:
        return {}

    names = [(p.get("name") or "").strip() for p in profile.projects]

    # 1) 完全一致
    for p, name in zip(profile.projects, names, strict=True):
        if name == project_name.strip():
            return p

    # 2) 互相包含
    target = project_name.strip()
    for p, name in zip(profile.projects, names, strict=True):
        if name and (target in name or name in target):
            return p

    # 3) 字符集覆盖率
    # 「AI 求职助手」vs「Echo AI 助手 App」——中间隔着「求职」，
    # 连续子串只有 "AI "，但字符集覆盖了 5/7，用户其实指的就是这个项目。
    def coverage(a: str, b: str) -> float:
        sa = {c for c in a if not c.isspace()}
        sb = {c for c in b if not c.isspace()}
        if len(sa) < 3:
            return 0.0
        common = sa & sb
        if len(common) < 2:
            return 0.0
        return len(common) / len(sa)

    best: dict = {}
    best_score = 0.0
    for p, name in zip(profile.projects, names, strict=True):
        if not name:
            continue
        score = coverage(target, name)
        if score > best_score:
            best_score = score
            best = p

    # 字符集容易高分，阈值给高一点，避免关联到无关项目。
    # 实测「AI 求职助手」对「Echo AI 助手 App…」是 4/6=0.67，所以取 0.6。
    return best if best_score >= 0.6 else {}


def review_resume_vs_code(profile: Profile, project_name: str, code_context: str, llm) -> dict:
    """对照项目代码审查简历里的该项目描述。"""
    proj = _find_project(profile, project_name)
    if not proj:
        return {
            "error": f"简历里没有找到「{project_name}」这个项目",
            "verdict": "",
            "inaccurate": [],
            "missing": [],
            "rewrites": [],
            "cut": [],
        }

    bullets = "\n".join(f"- {b}" for b in (proj.get("bullets") or []))
    resume_text = f"{proj.get('name', '')}\n{bullets}".strip()

    prompt = REVIEW_PROMPT.format(
        resume_project=resume_text,
        code=(code_context or "")[:4000] or "（没有代码摘要）",
    )
    try:
        raw = llm.complete("你是一个务实的简历审查员，只依据事实说话。", prompt, temperature=0.2)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group()) if m else {}
    except Exception as e:  # noqa: BLE001
        return {
            "error": f"{type(e).__name__}: {e}",
            "verdict": "",
            "inaccurate": [],
            "missing": [],
            "rewrites": [],
            "cut": [],
        }

    return {
        "project": proj.get("name", ""),
        "verdict": data.get("verdict") or "",
        "inaccurate": data.get("inaccurate") or [],
        "missing": data.get("missing") or [],
        "rewrites": data.get("rewrites") or [],
        "cut": data.get("cut") or [],
    }


def generate_greeting(
    profile: Profile,
    title: str,
    company: str,
    jd: str,
    llm,
    extra: str = "",
    max_jd: int = 2000,
) -> str:
    """针对岗位生成打招呼消息。"""
    prompt = GREET_PROMPT.format(
        profile=build_profile_text(profile),
        title=title,
        company=company,
        jd=(jd or "")[:max_jd],
        extra=extra or "无",
    )
    try:
        text = llm.complete("你是一个务实的求职顾问，说话不油腻。", prompt, temperature=0.6)
    except Exception as e:  # noqa: BLE001
        return f"生成失败：{type(e).__name__}"
    return text.strip().strip('"').strip()



def match_job(
    profile: Profile, title: str, company: str, jd: str, llm, max_jd: int = 2500
) -> dict:
    """评估一个岗位的匹配度。"""
    prompt = MATCH_PROMPT.format(
        profile=build_profile_text(profile),
        title=title,
        company=company,
        jd=(jd or "")[:max_jd],
    )
    try:
        raw = llm.complete("你是一个严格的求职顾问。", prompt, temperature=0.0)
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group()) if m else {}
    except Exception as e:  # noqa: BLE001
        return {"score": 0, "verdict": "未知", "matched": [], "missing": [],
                "reason": f"评估失败：{type(e).__name__}", "error": True}

    return {
        "score": int(data.get("score") or 0),
        "verdict": data.get("verdict") or "观望",
        "matched": data.get("matched") or [],
        "missing": data.get("missing") or [],
        "reason": data.get("reason") or "",
    }
