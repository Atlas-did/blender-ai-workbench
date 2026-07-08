"""
panel_chat.py — 聊天面板入口
=============================
在 Blender 3D Viewport 侧边栏注册 AIWork 聊天面板。
"""

from __future__ import annotations

import bpy
from bpy.types import Panel

from ..settings import PANEL_CATEGORY
from ..ui.ui_chat import draw_chat_panel
from ..ui.ui_logs import draw_logs_panel


class AIWORK_PT_Chat(Panel):
    """AIWork 主聊天面板。"""
    bl_label = "AI 助手"
    bl_idname = "AIWORK_PT_Chat"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY
    bl_order = 10

    def draw(self, context: bpy.types.Context) -> None:
        draw_chat_panel(self.layout, context)


class AIWORK_PT_ChatContext(Panel):
    """上下文面板 — 显示当前采集的 Blender 上下文详细信息。"""
    bl_label = "上下文"
    bl_idname = "AIWORK_PT_ChatContext"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY
    bl_order = 20
    bl_parent_id = "AIWORK_PT_Chat"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: bpy.types.Context) -> None:
        from .. import state

        layout = self.layout
        session = state.get_current_session()

        if session is None or session.context_snapshot is None:
            layout.label(text="暂无上下文", icon="INFO")
            layout.operator("aiwork.refresh_context", text="采集上下文", icon="FILE_REFRESH")
            return

        snap = session.context_snapshot

        # 场景信息
        box = layout.box()
        box.label(text="📐 场景", icon="SCENE_DATA")
        s = snap.scene
        box.label(text=f"名称: {s.scene_name or '(未命名)'}")
        box.label(text=f"对象数: {s.object_count}")
        box.label(text=f"当前帧: {s.current_frame}  [{s.frame_start}-{s.frame_end}]")
        box.label(text=f"渲染引擎: {s.render_engine or '(默认)'}")

        # 选中对象
        if s.selected_objects:
            box = layout.box()
            box.label(text=f"✅ 选中对象 ({len(s.selected_objects)})", icon="OBJECT_DATA")
            for obj in s.selected_objects:
                row = box.row(align=True)
                row.label(text=f"  {obj.name}", icon=_safe_obj_icon(obj.type))
                row.label(text=f"({obj.type})")

        # 工程信息
        p = snap.project
        if p.blend_filepath:
            box = layout.box()
            box.label(text="📁 文件", icon="FILE")
            box.label(text=f"路径: {p.blend_filepath}")
            box.label(text=f"状态: {'已保存' if p.is_saved else '未保存'}")

        layout.operator("aiwork.refresh_context", text="刷新上下文", icon="FILE_REFRESH")


class AIWORK_PT_ChatLogs(Panel):
    """日志面板。"""
    bl_label = "日志"
    bl_idname = "AIWORK_PT_ChatLogs"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = PANEL_CATEGORY
    bl_order = 30
    bl_parent_id = "AIWORK_PT_Chat"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: bpy.types.Context) -> None:
        draw_logs_panel(self.layout)


# 对象类型 → Blender 图标名映射（处理 Blender 类型名与图标名不一致的情况）
_OBJ_TYPE_ICON_MAP = {
    "LIGHT_PROBE": "OUTLINER_OB_LIGHTPROBE",
    "GPENCIL": "OUTLINER_OB_GREASEPENCIL",
}

# 已知安全的 OUTLINER_OB_ 图标前缀集合
_VALID_OBJ_ICON_TYPES = frozenset({
    "MESH", "CURVE", "SURFACE", "META", "FONT", "CURVES",
    "POINTCLOUD", "VOLUME", "ARMATURE", "LATTICE", "EMPTY",
    "LIGHT", "CAMERA", "SPEAKER", "LIGHTPROBE", "GREASEPENCIL",
    "FORCE_FIELD", "GROUP_INSTANCE", "IMAGE",
})


def _safe_obj_icon(obj_type: str) -> str:
    """安全获取对象类型对应的 Blender 图标名。"""
    if obj_type in _OBJ_TYPE_ICON_MAP:
        return _OBJ_TYPE_ICON_MAP[obj_type]
    if obj_type in _VALID_OBJ_ICON_TYPES:
        return f"OUTLINER_OB_{obj_type}"
    return "OBJECT_DATA"  # 安全的回退图标
