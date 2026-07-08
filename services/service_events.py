"""
service_events.py — 事件分发与消息总线
=======================================
插件内部的事件系统：
- 消息到达事件 → UI 刷新
- 工具执行完成事件 → 结果回写
- 连接状态变更事件 → 状态指示器更新
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)
