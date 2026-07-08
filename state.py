"""
state.py — 运行时状态容器
==========================
维护插件运行时的全局状态：当前会话、消息列表、连接状态、待执行工具等。
模块级变量作为单例使用（Blender 插件中全局唯一）。
"""

from __future__ import annotations

from .schemas import (
    ConnectionState,
    Message,
    RuntimeState,
    Session,
    ToolCall,
)

# ---------------------------------------------------------------------------
# 全局单例状态
# ---------------------------------------------------------------------------
_state = RuntimeState()


def get_state() -> RuntimeState:
    """获取当前运行时状态。"""
    return _state


def reset_state() -> None:
    """重置所有运行时状态（用于新建会话 / 重新加载）。"""
    global _state
    _state = RuntimeState()


# ---------------------------------------------------------------------------
# 便捷访问器
# ---------------------------------------------------------------------------

def get_current_session() -> Session | None:
    return _state.current_session


def set_current_session(session: Session) -> None:
    _state.current_session = session
    # 确保 session 在 sessions 列表中
    if session not in _state.sessions:
        _state.sessions.append(session)


def new_session() -> Session:
    """创建新会话并设为当前。"""
    session = Session()
    set_current_session(session)
    return session


def add_message(msg: Message) -> None:
    """向当前会话添加消息。"""
    if _state.current_session is None:
        new_session()
    assert _state.current_session is not None
    _state.current_session.add_message(msg)


def get_messages() -> list[Message]:
    """获取当前会话所有消息。"""
    if _state.current_session is None:
        return []
    return _state.current_session.messages


def set_connection_state(cs: ConnectionState) -> None:
    _state.connection_state = cs


def is_processing() -> bool:
    return _state.is_processing


def set_processing(flag: bool) -> None:
    _state.is_processing = flag


def set_last_error(err: str) -> None:
    _state.last_error = err


def add_pending_tool_call(tc: ToolCall) -> None:
    _state.pending_tool_calls.append(tc)


def clear_pending_tools() -> None:
    _state.pending_tool_calls.clear()
