"""BOSS直聘适配器。

注意：站点 DOM 会变。所以这里的选择器全部提成类常量，
以后抓的 HTML 里对不上，只改这几个常量即可，不用动逻辑。
"""

from __future__ import annotations

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from job_scout.models import JobPosting, SearchQuery, Source
from job_scout.sources import SourceAdapter

# BOSS 的城市编码。加城市就往这里加一条。
CITY_CODES: dict[str, str] = {
    "全国": "100010000",
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    "杭州": "101210100",
    "成都": "101270100",
    "武汉": "101200100",
    "南京": "101190100",
}


class BossAdapter(SourceAdapter):
    name = "boss"

    SEARCH_URL = "https://www.zhipin.com/web/geek/jobs"

    # ---- 选择器（站点改版时只改这里）----
    SEL_CARD = "li.job-card-wrapper"
    SEL_LINK = "a[href*='/job_detail/']"
    SEL_TITLE = ".job-name"
    SEL_AREA = ".job-area"
    SEL_SALARY = ".salary, .job-salary"
    SEL_COMPANY = ".company-name"
    SEL_TAGS = ".tag-list li, .job-card-footer .tag-list li"

    # 登录后才会出现的元素，用来判断登录状态（待用真实页面校验）
    LOGIN_MARKER = ".user-nav .user-name, .header-user-info"

    def search_url(self, query: SearchQuery) -> str:
        city_code = CITY_CODES.get(query.city, CITY_CODES["全国"])
        params = {"query": query.keyword, "city": city_code}
        return f"{self.SEARCH_URL}?{urlencode(params)}"

    def parse_list(self, html: str) -> list[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.SEL_CARD)
        if not cards:
            raise ValueError(
                f"没有匹配到岗位卡片（selector: {self.SEL_CARD}）。\n"
                "可能原因：1) 页面未登录 2) 站点改版 3) 被验证码拦截。\n"
                "把保存的 HTML 打开看一眼，再调整 BossAdapter 里的 SEL_* 常量。"
            )

        postings: list[JobPosting] = []
        for card in cards:
            link = card.select_one(self.SEL_LINK)
            href = link.get("href", "") if link else ""

            job_id = self._extract_job_id(href)
            title = self._pick(card, self.SEL_TITLE)
            if not job_id or not title:
                continue  # 广告卡片、推荐卡片跳过

            area = self._pick(card, self.SEL_AREA)
            city, district = self._split_area(area)
            salary_raw = self._pick(card, self.SEL_SALARY)
            smin, smax = self._parse_salary(salary_raw)

            tags = [t.get_text(strip=True) for t in card.select(self.SEL_TAGS)]

            postings.append(
                JobPosting(
                    source=Source.BOSS,
                    job_id=job_id,
                    title=title,
                    company=self._pick(card, self.SEL_COMPANY),
                    salary_raw=salary_raw or None,
                    salary_min_k=smin,
                    salary_max_k=smax,
                    city=city,
                    district=district,
                    skills=[t for t in tags if t],
                    url=f"https://www.zhipin.com{href}" if href.startswith("/") else href or None,
                )
            )
        return postings

    def parse_detail(self, html: str, base: JobPosting) -> JobPosting:
        soup = BeautifulSoup(html, "html.parser")
        desc = soup.select_one(".job-sec-text, .job-detail-section .text")
        if desc:
            base = base.model_copy(update={"description": desc.get_text("\n", strip=True)})
        return base

    # ---- 小工具 ----

    @staticmethod
    def _pick(card, selector: str) -> str:
        el = card.select_one(selector)
        return el.get_text(strip=True) if el else ""

    @staticmethod
    def _extract_job_id(href: str) -> str:
        # /job_detail/xxxxx.html?lid=... -> xxxxx
        if "/job_detail/" not in href:
            return ""
        return href.split("/job_detail/")[-1].split(".html")[0].split("?")[0]

    @staticmethod
    def _split_area(area: str) -> tuple[str | None, str | None]:
        if not area:
            return None, None
        parts = area.replace("·", " ").split()
        if len(parts) >= 2:
            return parts[0], parts[1]
        return (parts[0] if parts else None), None

    @staticmethod
    def _parse_salary(raw: str) -> tuple[float | None, float | None]:
        """'15-25K' / '15-25K·13薪' / '200-300元/天' -> (15, 25)"""
        from job_scout.salary import parse_salary

        return parse_salary(raw)

    # ---- 接口响应解析（CDP 旁听模式用这个，比 DOM 稳）----

    # BOSS 的风控返回码
    RISK_CODES = {31, 37}

    def parse_api_joblist(self, payload: dict) -> list[JobPosting]:
        """解析 /wapi/zpgeek/search/joblist.json 的响应。

        接口里的 salaryDesc 是明文，DOM 里的是字体加密的——
        这就是为什么走接口比抠 DOM 靠谱。
        """
        code = payload.get("code")
        message = payload.get("message") or ""

        if code in self.RISK_CODES:
            raise RiskControlError(f"触发风控：code={code} message={message}")
        if code not in (0, None):
            raise ValueError(f"接口返回异常：code={code} message={message}")

        jobs = ((payload.get("zpData") or {}).get("jobList")) or []
        postings: list[JobPosting] = []

        for job in jobs:
            job_id = job.get("encryptJobId") or job.get("jobId")
            title = job.get("jobName")
            if not job_id or not title:
                continue

            salary_raw = job.get("salaryDesc")
            smin, smax = self._parse_salary(salary_raw or "")

            postings.append(
                JobPosting(
                    source=Source.BOSS,
                    job_id=str(job_id),
                    title=title,
                    company=job.get("brandName") or "",
                    salary_raw=salary_raw,
                    salary_min_k=smin,
                    salary_max_k=smax,
                    city=job.get("cityName"),
                    district=job.get("areaDistrict"),
                    experience=job.get("jobExperience"),
                    education=job.get("jobDegree"),
                    skills=[s for s in (job.get("skills") or []) if s],
                    url=self.detail_url(job),
                )
            )
        return postings

    def detail_url(self, job: dict) -> str:
        job_id = job.get("encryptJobId") or job.get("jobId") or ""
        base = f"https://www.zhipin.com/job_detail/{job_id}.html"
        params = {}
        if job.get("securityId"):
            params["securityId"] = job["securityId"]
        if job.get("lid"):
            params["lid"] = job["lid"]
        if params:
            from urllib.parse import urlencode

            base += "?" + urlencode(params)
        return base


class RiskControlError(RuntimeError):
    """命中 BOSS 风控时抛这个，调用方要停下来，不要重试。"""
