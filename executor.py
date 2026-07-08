"""
executor.py — 工具执行调度器
=============================
统一的工具执行入口。负责：
1. 接收工具调用请求（来自 AI 回复）
2. 校验参数
3. 按风险等级分流（低风险直接执行，中/高风险等待确认）
4. 执行工具并返回结果
5. 记录审计日志
"""

from __future__ import annotations

import logging
from typing import Any

import bpy

from . import state
from .schemas import Message, RiskLevel, Role, ToolCall, ToolCallStatus
from .tools_registry import execute_tool, get_tool, validate_arguments

log = logging.getLogger(__name__)


def dispatch_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    *,
    auto_confirm_low_risk: bool = True,
) -> ToolCall:
    """调度一次工具调用。

    Args:
        tool_name: 工具名称。
        arguments: 工具参数。
        auto_confirm_low_risk: 低风险工具是否自动执行（不弹出确认）。

    Returns:
        ToolCall 实例，包含执行状态和结果。
    """
    tc = ToolCall(tool_name=tool_name, arguments=arguments)

    # 1. 查工具定义
    entry = get_tool(tool_name)
    if entry is None:
        tc.status = ToolCallStatus.FAILED
        tc.error = f"未知工具: {tool_name}"
        log.warning("工具调用失败: %s", tc.error)
        return tc

    definition = entry["definition"]

    # 2. 参数校验
    is_valid, error = validate_arguments(tool_name, arguments)
    if not is_valid:
        tc.status = ToolCallStatus.FAILED
        tc.error = error
        log.warning("工具参数校验失败: %s → %s", tool_name, error)
        return tc

    # 3. 风险判定
    if definition.risk_level == RiskLevel.LOW and auto_confirm_low_risk:
        # 低风险直接执行
        return _execute(tc)
    else:
        # 中/高风险 → 加入待确认队列
        tc.status = ToolCallStatus.PENDING
        state.add_pending_tool_call(tc)
        log.info("工具 '%s' 等待用户确认 (风险: %s)", tool_name, definition.risk_level.value)
        return tc


def execute_pending_tools() -> list[ToolCall]:
    """执行所有已批准的工具调用。

    在用户点击"确认全部"后调用。
    """
    pending = state.get_state().pending_tool_calls
    results: list[ToolCall] = []

    for tc in pending:
        if tc.status == ToolCallStatus.APPROVED:
            _execute(tc)
            results.append(tc)
        elif tc.status == ToolCallStatus.PENDING:
            # 仍然 pending 的跳过（不应该出现在确认后的列表中）
            pass

    state.clear_pending_tools()
    return results


def _execute(tc: ToolCall) -> ToolCall:
    """实际执行工具，更新状态和结果。"""
    tc.status = ToolCallStatus.RUNNING

    try:
        result = execute_tool(tc.tool_name, tc.arguments)
        tc.result = result
        tc.status = ToolCallStatus.DONE
        log.info("工具执行成功: %s", tc.tool_name)

    except Exception as exc:
        tc.error = str(exc)
        tc.status = ToolCallStatus.FAILED
        log.exception("工具执行失败: %s", tc.tool_name)

    # 把工具结果作为消息写入当前会话
    session = state.get_current_session()
    if session:
        msg = Message(
            role=Role.TOOL,
            content=(
                f"工具: {tc.tool_name}\n"
                f"状态: {tc.status.value}\n"
                f"结果: {tc.result if tc.status == ToolCallStatus.DONE else tc.error}"
            ),
            tool_calls=[tc],
        )
        session.add_message(msg)

    return tc


def execute_tool_calls(tool_calls: list[ToolCall]) -> list[ToolCall]:
    """批量执行工具调用（外部入口）。

    每个工具走 dispatch → 低风险自动跑，高风险等确认。
    """
    return [dispatch_tool_call(tc.tool_name, tc.arguments) for tc in tool_calls]
