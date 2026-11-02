"""站点适配器：每个招聘站点实现同一套接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from job_scout.models import JobPosting, SearchQuery


class SourceAdapter(ABC):
    """借鉴 Dify 的节点抽象：站点差异收敛在适配器内部，图只认接口。"""

    name: str

    @abstractmethod
    def search_url(self, query: SearchQuery) -> str:
        """返回搜索列表页 URL。"""

    @abstractmethod
    def parse_list(self, html: str) -> list[JobPosting]:
        """从列表页 HTML 解析出岗位（可只含卡片上的浅字段）。"""

    @abstractmethod
    def parse_detail(self, html: str, base: JobPosting) -> JobPosting:
        """从详情页补全完整 JD。"""
