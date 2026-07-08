"""operators/ — Blender Operator 注册。"""

from __future__ import annotations

import bpy

from .op_chat_send import AIWORK_OT_ChatSend, AIWORK_OT_ChatRetry
from .op_chat_clear import AIWORK_OT_ChatClear, AIWORK_OT_ChatNewSession
from .op_refresh_context import AIWORK_OT_RefreshContext
from .op_tool_confirm import AIWORK_OT_ConfirmAllTools, AIWORK_OT_CancelAllTools
from .op_tool_execute import AIWORK_OT_ToolExecute
from .op_open_file import AIWORK_OT_OpenFile
from .op_update import AIWORK_OT_CheckUpdate, AIWORK_OT_GitLog
from .op_mcp import AIWORK_OT_MCPStart, AIWORK_OT_MCPStop, AIWORK_OT_MCPRestart

CLASSES = [
    AIWORK_OT_ChatSend, AIWORK_OT_ChatRetry,
    AIWORK_OT_ChatClear, AIWORK_OT_ChatNewSession,
    AIWORK_OT_RefreshContext,
    AIWORK_OT_ConfirmAllTools, AIWORK_OT_CancelAllTools,
    AIWORK_OT_ToolExecute,
    AIWORK_OT_OpenFile,
    AIWORK_OT_CheckUpdate, AIWORK_OT_GitLog,
    AIWORK_OT_MCPStart, AIWORK_OT_MCPStop, AIWORK_OT_MCPRestart,
]

register_class, unregister_class = bpy.utils.register_classes_factory(CLASSES)


def register():
    register_class()


def unregister():
    unregister_class()
