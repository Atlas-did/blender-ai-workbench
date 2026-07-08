"""
service_bridge.py — Blender 与本地服务之间的总桥接
====================================================
负责管理 Blender 插件与外部本地服务之间的通信生命周期：
- 启动/停止本地服务
- 管理 WebSocket / HTTP 连接
- 消息路由和序列化

当前为骨架，后续实现。
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)
