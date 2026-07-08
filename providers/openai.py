"""OpenAI Provider — 复用 Moonshot 的实现（OpenAI 兼容协议）。"""

from __future__ import annotations

from .base import BaseProvider, ProviderInfo
from .moonshot import MoonshotProvider


class OpenAIProvider(MoonshotProvider):
    info = ProviderInfo(
        provider_id="openai",
        display_name="OpenAI",
        description="OpenAI GPT-4o / GPT-4.1 系列",
        default_endpoint="https://api.openai.com/v1",
        default_model="gpt-4o",
        default_api_key_env="OPENAI_API_KEY",
    )

    def list_models(self) -> list[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4-turbo",
            "o4-mini",
        ]
