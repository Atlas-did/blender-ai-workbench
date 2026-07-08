"""op_session.py — 会话切换 / 删除 Operator。"""

from __future__ import annotations

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from .. import state


class AIWORK_OT_SwitchSession(Operator):
    """切换到指定会话"""
    bl_idname = "aiwork.switch_session"
    bl_label = "切换会话"
    bl_description = "切换到该历史会话"
    bl_options = {'REGISTER', 'UNDO'}

    session_id: StringProperty(name="会话 ID")

    def execute(self, context: bpy.types.Context) -> set[str]:
        sessions = state.get_state().sessions
        for s in sessions:
            if s.id == self.session_id:
                state.set_current_session(s)
                self.report({'INFO'}, f"已切换到: {s.title}")
                return {'FINISHED'}
        self.report({'WARNING'}, "会话未找到")
        return {'CANCELLED'}


class AIWORK_OT_DeleteSession(Operator):
    """删除指定会话"""
    bl_idname = "aiwork.delete_session"
    bl_label = "删除会话"
    bl_description = "删除该历史会话"
    bl_options = {'REGISTER', 'UNDO'}

    session_id: StringProperty(name="会话 ID")

    def execute(self, context: bpy.types.Context) -> set[str]:
        sessions = state.get_state().sessions
        current = state.get_current_session()
        target = None
        for s in sessions:
            if s.id == self.session_id:
                target = s
                break
        if target is None:
            return {'CANCELLED'}

        sessions.remove(target)
        if current is target:
            state.set_current_session(sessions[-1] if sessions else state.new_session())
        self.report({'INFO'}, f"已删除: {target.title}")
        return {'FINISHED'}
