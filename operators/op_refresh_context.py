"""
op_refresh_context.py — 刷新上下文 Operator
============================================
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from .. import state
from ..context_builder import collect_context


class AIWORK_OT_RefreshContext(Operator):
    """手动刷新 Blender 上下文"""
    bl_idname = "aiwork.refresh_context"
    bl_label = "刷新上下文"
    bl_description = "重新采集当前场景、选中对象、文件等上下文信息"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        session = state.get_current_session()
        if session is None:
            session = state.new_session()

        session.context_snapshot = collect_context(context)

        self.report({'INFO'}, "上下文已刷新")
        return {'FINISHED'}
