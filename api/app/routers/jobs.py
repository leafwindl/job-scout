"""岗位接口：列表与详情。"""

from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, HTTPException, Query

from api.app.schemas import JobDetail, JobItem, JobListResponse
from job_scout.classify import classify
from job_scout.config import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_item(row: sqlite3.Row) -> JobItem:
    cat, _ = classify(row["description"] or "")
    try:
        skills = json.loads(row["skills"] or "[]")
    except Exception:
        skills = []
    return JobItem(
        job_id=row["job_id"],
        title=row["title"] or "",
        company=row["company"] or "",
        salary=row["salary_raw"] or "",
        city=row["city"] or "",
        district=row["district"] or "",
        experience=row["experience"] or "",
        category=cat,
        has_jd=bool(row["description"]),
        url=row["url"] or "",
        skills=skills,
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    keyword: str = "",
    category: str = "",
    district: str = "",
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> JobListResponse:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM postings WHERE title LIKE '%实习%' ORDER BY last_seen DESC"
    ).fetchall()
    conn.close()

    items = [_row_to_item(r) for r in rows]

    if keyword:
        kw = keyword.lower()
        items = [
            i
            for i in items
            if kw in i.title.lower() or kw in i.company.lower() or kw in " ".join(i.skills).lower()
        ]
    if category:
        items = [i for i in items if i.category == category]
    if district:
        items = [i for i in items if i.district == district]

    total = len(items)
    start = (page - 1) * size
    return JobListResponse(total=total, page=page, size=size, items=items[start : start + size])


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str) -> JobDetail:
    conn = _conn()
    row = conn.execute("SELECT * FROM postings WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="岗位不存在")

    base = _row_to_item(row)
    try:
        skills = json.loads(row["skills"] or "[]")
    except Exception:
        skills = []

    data = base.model_dump()
    data["description"] = row["description"] or ""
    data["skills"] = skills
    return JobDetail(**data)
