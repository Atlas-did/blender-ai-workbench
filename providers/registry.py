"""
providers/registry.py — Provider 注册中心
==========================================
Singleton 模式（参考 BlenderAIStudio 的 ModelRegistry）。
管理所有已注册的 LLM Provider。
"""

from __future__ import annotations

import logging
from typing import Optional

from .base import BaseProvider

log = logging.getLogger(__name__)

_providers: dict[str, BaseProvider] = {}


def register_provider(provider: BaseProvider) -> None:
    """注册一个 Provider。"""
    pid = provider.info.provider_id
    if pid in _providers:
        log.warning("Provider '%s' 已存在，将被覆盖", pid)
    _providers[pid] = provider
    log.info("Provider 已注册: %s", pid)


def unregister_provider(provider_id: str) -> None:
    """注销一个 Provider。"""
    if provider_id in _providers:
        del _providers[provider_id]
        log.info("Provider 已注销: %s", provider_id)


def get_provider(provider_id: str) -> BaseProvider:
    """获取 Provider 实例。"""
    p = _providers.get(provider_id)
    if p is None:
        raise ValueError(f"未知 Provider: {provider_id}. 可用: {list(_providers.keys())}")
    return p


def list_providers(self=None) -> list[BaseProvider]:
    """列出所有 Provider。"""
    return list(_providers.values())


def list_provider_ids() -> list[str]:
    """列出所有 Provider ID。"""
    return list(_providers.keys())


def get_default_provider_id() -> str:
    """获取默认 Provider ID。"""
    if _providers:
        return next(iter(_providers.keys()))
    return ""


def register_defaults() -> None:
    """注册内置 Provider。"""
    from .moonshot import MoonshotProvider
    from .openai import OpenAIProvider
    from .ollama import OllamaProvider

    register_provider(MoonshotProvider())
    register_provider(OpenAIProvider())
    register_provider(OllamaProvider())
    log.info("已注册 %d 个内置 Provider", len(_providers))
