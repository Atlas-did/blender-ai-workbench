"""
op_chat_clear.py — 清空会话 Operator
=====================================
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from .. import state


class AIWORK_OT_ChatClear(Operator):
    """清空当前会话"""
    bl_idname = "aiwork.chat_clear"
    bl_label = "清空会话"
    bl_description = "开始全新会话，清空当前消息历史"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        state.reset_state()
        state.new_session()
        self.report({'INFO'}, "会话已清空，开始新对话")
        return {'FINISHED'}


class AIWORK_OT_ChatNewSession(Operator):
    """新建会话（保留旧会话在历史中）"""
    bl_idname = "aiwork.chat_new_session"
    bl_label = "新建会话"
    bl_description = "创建新会话，旧会话保留在历史中"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        state.new_session()
        self.report({'INFO'}, "新会话已创建")
        return {'FINISHED'}
