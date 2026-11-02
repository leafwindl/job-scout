"""实习僧适配器。

实习僧网页版：https://www.shixiseng.com/interns
注意：它的城市参数用的是站点内部编码，不是中文。
这里先按「中文名 -> 站点编码」留表，第一次跑的时候把真实 URL 填进来。

TODO(verify): 用真实页面确认 CITY_CODES 与选择器。
"""

from __future__ import annotations

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from job_scout.models import JobPosting, SearchQuery, Source
from job_scout.sources import SourceAdapter

# 实习僧的城市参数（待校验，先用中文占位）
CITY_CODES: dict[str, str] = {
    "全国": "",
    "广州": " Guangzhou",
    "北京": "Beijing",
    "上海": "Shanghai",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
}


class ShixisengAdapter(SourceAdapter):
    name = "shixiseng"

    SEARCH_URL = "https://www.shixiseng.com/interns"

    # ---- 选择器（站点改版时只改这里）----
    SEL_CARD = ".intern-wrap.intern-item, .intern-item"
    SEL_LINK = "a[href*='/intern/']"
    SEL_TITLE = ".f-l.intern-detail__job span, .intern-detail__job"
    SEL_COMPANY = ".f-r.intern-detail__company, .intern-detail__company"
    SEL_SALARY = ".day, .intern-detail__salary"
    SEL_AREA = ".city, .intern-detail__city"

    LOGIN_MARKER = ".user-info, .avatar"

    def search_url(self, query: SearchQuery) -> str:
        params = {"keyword": query.keyword}
        city = CITY_CODES.get(query.city, "")
        if city:
            params["city"] = city
        return f"{self.SEARCH_URL}?{urlencode(params)}"

    def parse_list(self, html: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.SEL_CARD)
        if not cards:
            raise ValueError(
                f"没有匹配到实习卡片（selector: {self.SEL_CARD}）。\n"
                "站点可能改版或需要登录，检查保存的 HTML 后调整 SEL_* 常量。"
            )

        postings: list[JobPosting] = []
        for card in cards:
            link = card.select_one(self.SEL_LINK)
            href = link.get("href", "") if link else ""
            job_id = href.split("/intern/")[-1] if "/intern/" in href else ""
            title = self._pick(card, self.SEL_TITLE)
            if not job_id or not title:
                continue

            postings.append(
                JobPosting(
                    source=Source.SHIXISENG,
                    job_id=job_id,
                    title=title,
                    company=self._pick(card, self.SEL_COMPANY),
                    salary_raw=self._pick(card, self.SEL_SALARY) or None,
                    city=self._pick(card, self.SEL_AREA) or None,
                    url=f"https://www.shixiseng.com{href}" if href.startswith("/") else href or None,
                )
            )
        return postings

    def parse_detail(self, html: str, base: JobPosting) -> JobPosting:
        soup = BeautifulSoup(html, "html.parser")
        desc = soup.select_one(".job_detail .job_msg, .intern-detail__job-desc")
        if desc:
            base = base.model_copy(update={"description": desc.get_text("\n", strip=True)})
        return base

    @staticmethod
    def _pick(card, selector: str) -> str:
        el = card.select_one(selector)
        return el.get_text(strip=True) if el else ""
