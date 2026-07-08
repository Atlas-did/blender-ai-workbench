"""
op_open_file.py — 打开/预览文件 Operator
=========================================
在 Blender 文本编辑器中打开外部脚本、预览资源文件。
"""

from __future__ import annotations

import os

import bpy
from bpy.types import Operator


class AIWORK_OT_OpenFile(Operator):
    """打开或预览文件"""
    bl_idname = "aiwork.open_file"
    bl_label = "打开文件"
    bl_description = "在 Blender 文本编辑器中打开文件"
    bl_options = {'REGISTER', 'UNDO'}

    # 使用赋值语法而非纯注解，兼容 Blender bpy.props
    filepath: bpy.props.StringProperty = bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not self.filepath:
            self.report({'WARNING'}, "未选择文件")
            return {'CANCELLED'}

        if not os.path.exists(self.filepath):
            self.report({'ERROR'}, f"文件不存在: {self.filepath}")
            return {'CANCELLED'}

        try:
            text = bpy.data.texts.load(self.filepath)
        except Exception as exc:
            self.report({'ERROR'}, f"打开失败: {exc}")
            return {'CANCELLED'}

        # 尽量切到第一个文本编辑器区域
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'TEXT_EDITOR':
                    for space in area.spaces:
                        if space.type == 'TEXT_EDITOR':
                            space.text = text
                            break
                    break

        self.report({'INFO'}, f"已打开: {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
