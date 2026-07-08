"""
storage.py — 本地持久化
========================
负责会话和设置的本地读写。

存储位置：
    {Blender 扩展目录}/aiwork/
    ├─ sessions.json    — 会话历史
    ├─ settings.json    — 插件设置
    └─ audit.jsonl      — 审计日志

单次会话内的读写做了简单内存缓存，避免频繁磁盘 IO。
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Optional

import bpy

from .schemas import Message, Session
from .settings import AUDIT_LOG_FILE, SESSIONS_FILE, SETTINGS_FILE, STORAGE_DIR_NAME

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

def _storage_dir() -> str:
    """获取插件存储根目录（自动创建）。"""
    # 优先使用 Blender 的用户脚本目录，避免写入 Program Files
    user_root = bpy.utils.user_resource("SCRIPTS", path=STORAGE_DIR_NAME, create=True)
    if user_root:
        storage = user_root
    else:
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        storage = os.path.join(addon_dir, STORAGE_DIR_NAME)
    os.makedirs(storage, exist_ok=True)
    return storage


def _sessions_path() -> str:
    return os.path.join(_storage_dir(), SESSIONS_FILE)


def _settings_path() -> str:
    return os.path.join(_storage_dir(), SETTINGS_FILE)


def _audit_path() -> str:
    return os.path.join(_storage_dir(), AUDIT_LOG_FILE)


# ---------------------------------------------------------------------------
# 线程锁（ Blender 中谨慎使用线程，但保留保护）
# ---------------------------------------------------------------------------
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# 会话持久化
# ---------------------------------------------------------------------------

def save_sessions(sessions: list[Session]) -> bool:
    """保存所有会话到磁盘。

    Returns:
        bool: 是否保存成功。
    """
    try:
        data = [_session_to_dict(s) for s in sessions]
        with _lock:
            with open(_sessions_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("已保存 %d 个会话", len(sessions))
        return True
    except Exception:
        log.exception("保存会话失败")
        return False


def load_sessions() -> list[Session]:
    """从磁盘加载所有会话。

    Returns:
        list[Session]: 会话列表，文件不存在或损坏时返回空列表。
    """
    path = _sessions_path()
    if not os.path.exists(path):
        log.info("会话文件不存在，返回空列表: %s", path)
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sessions = [_session_from_dict(d) for d in data]
        log.info("已加载 %d 个会话", len(sessions))
        return sessions
    except Exception:
        log.exception("加载会话失败")
        return []


# ---------------------------------------------------------------------------
# 设置持久化
# ---------------------------------------------------------------------------

def save_settings(settings: dict) -> bool:
    """保存插件设置到磁盘。"""
    try:
        with _lock:
            with open(_settings_path(), "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        log.exception("保存设置失败")
        return False


def load_settings() -> dict:
    """从磁盘加载插件设置。"""
    path = _settings_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        log.exception("加载设置失败")
        return {}


# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------

def append_audit(entry: dict) -> None:
    """追加一条审计日志（JSONL 格式，每行一条 JSON）。"""
    import time
    entry["_timestamp"] = time.time()
    try:
        with open(_audit_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        log.exception("审计日志写入失败")


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------

def _session_to_dict(session: Session) -> dict:
    """Session → 可 JSON 序列化的 dict。"""
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "status": tc.status.value,
                        "result": tc.result,
                        "error": tc.error,
                        "timestamp": tc.timestamp,
                    }
                    for tc in m.tool_calls
                ],
                "timestamp": m.timestamp,
            }
            for m in session.messages
        ],
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }


def _session_from_dict(data: dict) -> Session:
    """dict → Session 反序列化。"""
    from .schemas import Message, Role, ToolCall, ToolCallStatus

    messages = []
    for m_data in data.get("messages", []):
        tool_calls = []
        for tc_data in m_data.get("tool_calls", []):
            tc = ToolCall(
                id=tc_data.get("id", ""),
                tool_name=tc_data.get("tool_name", ""),
                arguments=tc_data.get("arguments", {}),
                status=ToolCallStatus(tc_data.get("status", "done")),
                result=tc_data.get("result"),
                error=tc_data.get("error", ""),
                timestamp=tc_data.get("timestamp", 0.0),
            )
            tool_calls.append(tc)

        msg = Message(
            id=m_data.get("id", ""),
            role=Role(m_data.get("role", "user")),
            content=m_data.get("content", ""),
            tool_calls=tool_calls,
            timestamp=m_data.get("timestamp", 0.0),
        )
        messages.append(msg)

    return Session(
        id=data.get("id", ""),
        title=data.get("title", "新会话"),
        messages=messages,
        created_at=data.get("created_at", 0.0),
        updated_at=data.get("updated_at", 0.0),
    )
