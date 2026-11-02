"""配置：统一收口。搜索任务是数据，不是代码，所以放 YAML。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """来自 .env 的运行环境配置。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    model_name: str = "deepseek-chat"

    browser_profile_dir: str = ".playwright/profile"
    browser_channel: str = "msedge"  # msedge / chrome / 留空=自带 Chromium
    db_path: str = "data/job_scout.db"


class QuerySpec(BaseModel):
    """一条搜索任务。"""

    keyword: str
    city: str = "广州"
    max_pages: int = 5


class Limits(BaseModel):
    """全局采集限制。别调太激进。"""

    page_delay_ms: int = 3000
    detail_delay_ms: int = 2000
    max_detail_fetch: int = 80
    headless: bool = False


class SearchConfig(BaseModel):
    """configs/search.yaml 的结构。"""

    queries: list[QuerySpec]
    limits: Limits = Field(default_factory=Limits)


DEFAULT_CONFIG_PATH = Path("configs/search.yaml")


def load_search_config(path: str | Path = DEFAULT_CONFIG_PATH) -> SearchConfig:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到搜索配置：{p.resolve()}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return SearchConfig.model_validate(data)


settings = Settings()
