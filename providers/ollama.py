"""Ollama Provider — 本地模型（OpenAI 兼容协议）。"""

from __future__ import annotations

from .base import BaseProvider, ProviderInfo
from .moonshot import MoonshotProvider


class OllamaProvider(MoonshotProvider):
    info = ProviderInfo(
        provider_id="ollama",
        display_name="Ollama (本地)",
        description="Ollama 本地 LLM — http://localhost:11434/v1",
        default_endpoint="http://localhost:11434/v1",
        default_model="qwen2.5:7b",
        default_api_key_env="",
    )

    def list_models(self) -> list[str]:
        return [
            "qwen2.5:7b",
            "qwen2.5:14b",
            "qwen2.5:32b",
            "llama3.2:3b",
            "llama3.1:8b",
            "codellama:7b",
            "mistral:7b",
            "gemma3:12b",
            "deepseek-r1:8b",
        ]

    def validate_api_key(self, api_key: str) -> bool:
        # Ollama 不需要 API Key
        return True
