"""LLM 接入层：OpenAI 兼容协议，默认 DeepSeek。

设计要点：
- **可插拔**：没配置 key 时返回 None，上层降级为抽取式回答，而不是报错
- 只要兼容 OpenAI 协议（DeepSeek / 通义 / 硅基流动 / Ollama），改 base_url 即可
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from job_scout.config import settings


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str


def load_config() -> LLMConfig | None:
    """从统一配置读（pydantic-settings 会加载 .env）。

    早期版本用 os.getenv，导致 .env 里的 key 读不到，这里修正。
    """
    key = (settings.openai_api_key or "").strip()
    if not key:
        return None
    return LLMConfig(
        api_key=key,
        base_url=(settings.openai_base_url or "https://api.deepseek.com/v1").strip(),
        model=(settings.model_name or "deepseek-chat").strip(),
    )


class LLM:
    def __init__(self, config: LLMConfig) -> None:
        from openai import OpenAI

        self.config = config
        # 重排这类长 prompt 响应慢，默认超时不够（实测 APITimeoutError）
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=120.0,
            max_retries=1,
        )

    def complete(self, system: str, user: str, temperature: float = 0.0) -> str:
        resp = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def stream(self, system: str, user: str, temperature: float = 0.0) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


def get_llm() -> LLM | None:
    """没配 key 就返回 None，调用方降级处理。"""
    cfg = load_config()
    if cfg is None:
        return None
    try:
        return LLM(cfg)
    except Exception:
        return None
