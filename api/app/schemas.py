"""请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    k: int = Field(default=10, ge=1, le=50)


class SearchHit(BaseModel):
    job_id: str
    title: str
    company: str
    salary: str = ""
    district: str = ""
    url: str = ""
    score: float = 0.0
    skills: list[str] = Field(default_factory=list)
    category: str = ""


class SearchResponse(BaseModel):
    query: str
    total: int
    hits: list[SearchHit]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=10)


class Citation(BaseModel):
    index: int
    job_id: str
    title: str
    company: str
    district: str = ""
    salary: str = ""
    url: str = ""


class AskResponse(BaseModel):
    answer: str
    mode: str  # llm / extractive / refused
    citations: list[Citation] = Field(default_factory=list)
    docs_count: int = 0


class JobItem(BaseModel):
    job_id: str
    title: str
    company: str
    salary: str = ""
    city: str = ""
    district: str = ""
    experience: str = ""
    category: str = ""
    has_jd: bool = False
    url: str = ""
    skills: list[str] = Field(default_factory=list)


class JobListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[JobItem]


class JobDetail(JobItem):
    description: str = ""
    skills: list[str] = Field(default_factory=list)
