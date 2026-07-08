"""
audit.py — 审计日志记录与导出
==============================
记录所有工具调用、确认操作、错误事件，
支持按时间范围导出为 JSON / CSV。
"""

from __future__ import annotations

import logging
from typing import Any

from .storage import append_audit

log = logging.getLogger(__name__)


def log_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    error: str = "",
    user_confirmed: bool = False,
) -> None:
    """记录一次工具调用。"""
    append_audit({
        "event": "tool_call",
        "tool": tool_name,
        "arguments": arguments,
        "result": str(result)[:500] if result else None,
        "error": error,
        "user_confirmed": user_confirmed,
    })


def log_user_action(action: str, details: dict[str, Any] | None = None) -> None:
    """记录用户手动操作。"""
    append_audit({
        "event": "user_action",
        "action": action,
        "details": details or {},
    })


def log_error(source: str, error: str, context: dict[str, Any] | None = None) -> None:
    """记录错误事件。"""
    append_audit({
        "event": "error",
        "source": source,
        "error": error,
        "context": context or {},
    })
