"""数据模型：全项目统一用 Pydantic，LLM 抽取结果也要过校验。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Source(StrEnum):
    BOSS = "boss"
    SHIXISENG = "shixiseng"


class SearchQuery(BaseModel):
    """一次采集任务的定义。"""

    keyword: str = Field(description="搜索关键词，如 'Agent 开发'")
    city: str = "全国"
    salary_min_k: int | None = None
    experience: str | None = None
    max_pages: int = 5
    sources: list[Source] = Field(default_factory=lambda: [Source.BOSS])


class JobPosting(BaseModel):
    """一条岗位。字段尽量贴近分析需要，而非站点原始结构。"""

    source: Source
    job_id: str
    title: str
    company: str

    salary_raw: str | None = None
    salary_min_k: float | None = None
    salary_max_k: float | None = None

    city: str | None = None
    district: str | None = None
    experience: str | None = None
    education: str | None = None

    skills: list[str] = Field(default_factory=list)
    description: str | None = None
    url: str | None = None
    security_id: str | None = None

    collected_at: datetime = Field(default_factory=datetime.now)

    @property
    def dedupe_key(self) -> str:
        return f"{self.source.value}:{self.job_id}"


class ReportInput(BaseModel):
    """报告生成所需的聚合结果。"""

    total: int
    by_skill: dict[str, int] = Field(default_factory=dict)
    by_experience: dict[str, int] = Field(default_factory=dict)
    salary_median_k: float | None = None
    top_companies: list[tuple[str, int]] = Field(default_factory=list)
