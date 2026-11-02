"""把采集到的岗位数据渲染成一个单文件可视化看板。

设计取舍：
- 不启动服务器，直接生成一个 HTML，双击就能看（好分享、好存档）
- ECharts 内联进 HTML，离线也能用
- 统计在 Python 里算完再塞给前端，避免前端重复实现业务逻辑
"""

from __future__ import annotations

import json
import re
import sqlite3
import webbrowser
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from job_scout.classify import classify

TEMPLATE_PATH = Path(__file__).parent / "templates" / "dashboard.html"


# ---------------------------------------------------------------- 薪资归一化


def normalize_salary(raw: str | None) -> tuple[float | None, float | None, str]:
    """把各种薪资写法统一成「月薪 K」。

    返回 (min_k, max_k, kind)，kind 是 monthly / daily / unknown。
    '15-30K·16薪' -> (15.0, 30.0, 'monthly')
    '200-400元/天' -> (4.4, 8.8, 'daily')   # 按 22 天折算
    """
    if not raw:
        return None, None, "unknown"

    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[Kk]", raw)
    if m:
        return float(m.group(1)), float(m.group(2)), "monthly"

    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*元/天", raw)
    if m:
        lo = float(m.group(1)) * 22 / 1000
        hi = float(m.group(2)) * 22 / 1000
        return round(lo, 1), round(hi, 1), "daily"

    m = re.search(r"(\d+(?:\.\d+)?)\s*元/天", raw)
    if m:
        v = float(m.group(1)) * 22 / 1000
        return round(v, 1), round(v, 1), "daily"

    return None, None, "unknown"


SALARY_BUCKETS = [
    ("< 10K", 0, 10),
    ("10-15K", 10, 15),
    ("15-20K", 15, 20),
    ("20-30K", 20, 30),
    ("30-40K", 30, 40),
    ("40K+", 40, 10_000),
]

# JD 正文里要统计的技术词（名称, 正则）。统计的是「多少份 JD 提到」，不是出现次数。
TECH_TERMS: list[tuple[str, str]] = [
    ("Agent", r"agent|智能体"),
    ("大模型", r"大模型|llm"),
    ("RAG", r"\brag\b|检索增强"),
    ("知识库", r"知识库"),
    ("向量库", r"向量库|向量数据库|embedding|faiss|milvus|chroma|qdrant"),
    ("Prompt", r"prompt"),
    ("Function Calling", r"function\s*calling|tool\s*calling|工具调用"),
    ("Multi-Agent", r"multi[- ]?agent|多智能体|多\s*agent"),
    ("LangChain", r"langchain"),
    ("LangGraph", r"langgraph"),
    ("LlamaIndex", r"llamaindex"),
    ("AutoGen", r"autogen"),
    ("CrewAI", r"crewai"),
    ("Dify", r"dify"),
    ("Coze/扣子", r"coze|扣子"),
    ("MCP", r"\bmcp\b"),
    ("微调", r"微调|fine[- ]?tun|lora|\bsft\b"),
    ("模型部署", r"vllm|ollama|模型部署|部署模型|推理优化"),
    ("Python", r"python"),
    ("Java", r"java"),
    ("Golang", r"golang"),
    ("TypeScript/JS", r"typescript|javascript|\bjs\b|\bts\b"),
    ("C++", r"c\+\+"),
    ("FastAPI", r"fastapi"),
    ("Flask", r"flask"),
    ("Django", r"django"),
    ("Spring", r"spring"),
    ("PyTorch", r"pytorch"),
    ("MySQL", r"mysql"),
    ("PostgreSQL", r"postgres"),
    ("Redis", r"redis"),
    ("MongoDB", r"mongo"),
    ("Docker", r"docker"),
    ("K8s", r"k8s|kubernetes"),
    ("Linux", r"linux"),
    ("微服务", r"微服务|microservice"),
    ("分布式", r"分布式"),
    ("消息队列", r"kafka|rabbitmq|消息队列"),
    ("爬虫", r"爬虫|scrapy"),
    ("数据分析", r"pandas|数据分析"),
    ("开源/论文", r"开源项目|论文|顶会|github"),
]


def extract_jd_keywords(postings: list[dict[str, Any]]) -> tuple[list[list], int]:
    """统计每份 JD 是否提到某技术词，返回 (词频, JD 总数)。"""
    descs = [p.get("description") or "" for p in postings]
    descs = [d for d in descs if d]
    counter: Counter[str] = Counter()
    for d in descs:
        low = d.lower()
        for name, pat in TECH_TERMS:
            if re.search(pat, low):
                counter[name] += 1
    return [list(x) for x in counter.most_common(28)], len(descs)


def _bucket_of(avg: float) -> str:
    for label, lo, hi in SALARY_BUCKETS:
        if lo <= avg < hi:
            return label
    return SALARY_BUCKETS[-1][0]


# ---------------------------------------------------------------- 读取与统计


def load_postings(db_path: str | Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM postings").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def build_payload(postings: list[dict[str, Any]]) -> dict[str, Any]:
    # 看板只分析实习岗：标题必须含「实习」
    interns = [p for p in postings if "实习" in (p.get("title") or "")]

    items: list[dict[str, Any]] = []
    skill_counter: Counter[str] = Counter()
    exp_counter: Counter[str] = Counter()
    dist_counter: Counter[str] = Counter()
    company_counter: Counter[str] = Counter()
    bucket_counter: Counter[str] = Counter()
    salaries: list[float] = []
    with_jd = 0
    cat_counter: Counter[str] = Counter()

    for p in interns:
        lo, hi, kind = normalize_salary(p.get("salary_raw"))
        avg = round((lo + hi) / 2, 1) if lo is not None and hi is not None else None

        skills = []
        try:
            skills = json.loads(p.get("skills") or "[]")
        except Exception:
            skills = []

        for s in skills:
            if s:
                skill_counter[s] += 1
        if p.get("experience"):
            exp_counter[p["experience"]] += 1
        if p.get("district"):
            dist_counter[p["district"]] += 1
        if p.get("company"):
            company_counter[p["company"]] += 1
        if avg is not None:
            bucket_counter[_bucket_of(avg)] += 1
            salaries.append(avg)

        desc = p.get("description") or ""
        if desc:
            with_jd += 1
        category, _ = classify(desc)
        cat_counter[category] += 1

        items.append(
            {
                "title": p.get("title") or "",
                "company": p.get("company") or "",
                "salary": p.get("salary_raw") or "",
                "city": p.get("city") or "",
                "district": p.get("district") or "",
                "experience": p.get("experience") or "",
                "education": p.get("education") or "",
                "skills": skills,
                "url": p.get("url") or "",
                "avg_k": avg,
                "kind": kind,
                "has_jd": bool(desc),
                "jd_len": len(desc),
                "category": category,
            }
        )

    salaries.sort()
    median = salaries[len(salaries) // 2] if salaries else None

    jd_keywords, jd_total = extract_jd_keywords(interns)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(items),
        "with_salary": len(salaries),
        "with_jd": with_jd,
        "jd_total": jd_total,
        "jd_keywords": jd_keywords,
        "categories": cat_counter.most_common(),
        "median_k": median,
        "skill_kinds": len(skill_counter),
        "postings": items,
        "salary_buckets": {label: bucket_counter.get(label, 0) for label, _, _ in SALARY_BUCKETS},
        "skills": skill_counter.most_common(20),
        "experience": exp_counter.most_common(),
        "districts": dist_counter.most_common(12),
        "companies": company_counter.most_common(10),
    }


# ---------------------------------------------------------------- 渲染


def _echarts_source() -> str:
    """优先内联本地 echarts，找不到就退回 CDN。"""
    for base in (Path(__file__).parents[2], Path.cwd()):
        js = base / "static" / "echarts.min.js"
        if js.exists():
            return f"<script>{js.read_text(encoding='utf-8')}</script>"
    return (
        '<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>'
    )


def render(db_path: str | Path = "data/job_scout.db") -> Path:
    postings = load_postings(db_path)
    payload = build_payload(postings)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    html = (
        template.replace("/*__ECHARTS__*/", _echarts_source())
        .replace("/*__DATA__*/", data_json)
        .replace("__TOTAL__", str(payload["total"]))
        .replace("__GENERATED__", payload["generated_at"])
    )

    out = Path("data/dashboard.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def open_dashboard(path: Path) -> None:
    webbrowser.open(path.resolve().as_uri())
