"""
providers/ — LLM Provider 包
=============================
参考 BlenderAIStudio studio/providers/ 设计。

每个 Provider 封装模型列表、请求构建、响应解析、连接测试。
通过 registry.register_defaults() 注册内置 Provider。
"""

from __future__ import annotations

import bpy

from .registry import register_defaults, _providers

modules = []


def register():
    register_defaults()


def unregister():
    _providers.clear()
