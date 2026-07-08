"""
schemas.py — 数据结构定义
==========================
使用 Python dataclass 定义项目核心数据结构。
所有模块通过这里的类型来交换数据，保证一致性。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════════════════════════════════════════

class Role(str, Enum):
    """消息发送者角色。"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class RiskLevel(str, Enum):
    """工具风险等级，对应确认策略。"""
    LOW = "low"         # 纯读取 — 无需确认
    MEDIUM = "medium"   # 修改场景 — 需要确认（可批量）
    HIGH = "high"       # 执行代码 / 文件操作 — 必须逐个确认


class ToolCallStatus(str, Enum):
    """工具调用的执行状态。"""
    PENDING = "pending"         # 等待确认
    APPROVED = "approved"       # 已批准，等待执行
    RUNNING = "running"         # 执行中
    DONE = "done"               # 执行成功
    FAILED = "failed"           # 执行失败
    CANCELLED = "cancelled"     # 用户取消


class ConnectionState(str, Enum):
    """与 LLM 服务的连接状态。"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


# ═══════════════════════════════════════════════════════════════════════════════
# 上下文
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SceneObjectInfo:
    """单个场景对象的摘要信息。"""
    name: str
    type: str              # e.g. 'MESH', 'CAMERA', 'LIGHT'
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    visible: bool = True
    selected: bool = False
    children_count: int = 0


@dataclass
class SceneContext:
    """当前场景的上下文快照。"""
    scene_name: str = ""
    object_count: int = 0
    active_object_name: str = ""
    selected_objects: list[SceneObjectInfo] = field(default_factory=list)
    visible_objects: list[SceneObjectInfo] = field(default_factory=list)
    current_frame: int = 1
    frame_start: int = 1
    frame_end: int = 250
    render_engine: str = ""
    world_name: str = ""


@dataclass
class ProjectContext:
    """当前项目/文件的上下文。"""
    blend_filepath: str = ""
    blend_filename: str = ""
    is_saved: bool = False
    recent_scripts: list[str] = field(default_factory=list)


@dataclass
class ContextSnapshot:
    """发给 AI 的完整上下文包。"""
    timestamp: float = field(default_factory=time.time)
    scene: SceneContext = field(default_factory=SceneContext)
    project: ProjectContext = field(default_factory=ProjectContext)
    custom: dict[str, Any] = field(default_factory=dict)

    def to_text(self) -> str:
        """把上下文序列化为 AI 可读的文本块。"""
        parts = ["[Blender 上下文]"]
        parts.append(f"场景: {self.scene.scene_name}")
        if self.scene.active_object_name:
            parts.append(f"活动对象: {self.scene.active_object_name}")
        parts.append(f"文件: {self.project.blend_filename or '(未保存)'}")
        parts.append(f"选中对象 ({len(self.scene.selected_objects)}):")
        for obj in self.scene.selected_objects:
            parts.append(f"  - {obj.name} ({obj.type}) @ {obj.location}")
        parts.append(f"当前帧: {self.scene.current_frame} / {self.scene.frame_start}-{self.scene.frame_end}")
        recent_events = self.custom.get("recent_events") or []
        if recent_events:
            parts.append("最近操作:")
            for event in recent_events[-8:]:
                parts.append(f"  - {event}")
        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# 消息与会话
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolParameter:
    """工具参数定义（用于注册和校验）。"""
    name: str
    param_type: str       # 'string', 'number', 'boolean', 'object'
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """工具定义（注册在 tools_registry 中）。"""
    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class ToolCall:
    """一次具体的工具调用实例。"""
    id: str = field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    status: ToolCallStatus = ToolCallStatus.PENDING
    result: Any = None
    error: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Message:
    """一条聊天消息。可以是文本或工具调用。"""
    id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    role: Role = Role.USER
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """一次对话会话。"""
    id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:8]}")
    title: str = "新会话"
    messages: list[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    context_snapshot: Optional[ContextSnapshot] = None

    def add_message(self, msg: Message) -> None:
        self.messages.append(msg)
        self.updated_at = time.time()
        # 自动取首条用户消息做标题
        if self.title == "新会话" and msg.role == Role.USER:
            self.title = msg.content[:40] + ("…" if len(msg.content) > 40 else "")


# ═══════════════════════════════════════════════════════════════════════════════
# 运行时状态
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RuntimeState:
    """插件运行时全局状态（单例，放在 state.py 模块中）。"""
    current_session: Optional[Session] = None
    sessions: list[Session] = field(default_factory=list)
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    is_processing: bool = False
    last_error: str = ""
    pending_tool_calls: list[ToolCall] = field(default_factory=list)
    tool_chain_depth: int = 0
    recent_events: list[str] = field(default_factory=list)
    last_context_signature: str = ""
    attachments: list[dict] = field(default_factory=list)  # 用户附加的文件
