"""RAG 语料层：把数据库里的岗位变成可检索的文档。

设计决策（面试可讲）：
- **一条 JD = 一个 chunk**。JD 本身是完整语义单元，按 token 硬切会破坏
  「岗位职责 / 任职要求」的内部结构，反而降低检索质量。
- 检索文本 = 标题 + 公司 + 城市 + 技能标签 + 命中的技术词 + 正文。
  前面这些结构化字段是「免费的高质量信号」，很多 RAG 项目只用了正文。
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from job_scout.classify import classify
from job_scout.dashboard import TECH_TERMS


@dataclass
class Doc:
    doc_id: str
    title: str
    company: str
    text: str          # 增强版：结构化字段 + 正文
    text_raw: str      # 仅标题 + 正文，用于做 A/B 对比
    meta: dict = field(default_factory=dict)


def _matched_terms(text: str) -> list[str]:
    low = text.lower()
    return [name for name, pat in TECH_TERMS if re.search(pat, low)]


def build_doc(row: sqlite3.Row) -> Doc:
    title = row["title"] or ""
    company = row["company"] or ""
    city = row["city"] or ""
    district = row["district"] or ""
    desc = row["description"] or ""

    try:
        skills = json.loads(row["skills"] or "[]")
    except Exception:
        skills = []

    terms = _matched_terms(desc)
    category, _ = classify(desc)

    # 结构化字段前置：BM25 对标题/技能命中的权重天然更高
    head = " ".join([title, company, city, district, *skills, *terms])
    text = f"{head}\n{desc}"

    return Doc(
        doc_id=row["job_id"],
        title=title,
        company=company,
        text=text,
        text_raw=f"{title} {company}\n{desc}",
        meta={
            "city": city,
            "district": district,
            "salary": row["salary_raw"] or "",
            "experience": row["experience"] or "",
            "url": row["url"] or "",
            "category": category,
            "skills": skills,
            "terms": terms,
            "is_intern": "实习" in title,
        },
    )


def load_docs(
    db_path: str | Path = "data/job_scout.db",
    only_intern: bool = False,
    require_jd: bool = True,
) -> list[Doc]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    sql = "SELECT * FROM postings WHERE 1=1"
    if only_intern:
        sql += " AND title LIKE '%实习%'"
    # 只取标题相关的：销售/助教/运营这类即使抓了 JD 也不进语料
    sql += " AND is_relevant = 1"
    if require_jd:
        sql += " AND description IS NOT NULL AND description != ''"

    rows = conn.execute(sql).fetchall()
    conn.close()
    return [build_doc(r) for r in rows]
