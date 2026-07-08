"""
ui_settings.py — 设置面板 UI
=============================
插件设置页的独立面板（补充 preferences.py 的偏好设置）。
可在 3D View 侧栏或独立窗口中打开。
"""

from __future__ import annotations

import bpy

from ..preferences import get_prefs
from . import ui_common as uc


def draw_settings_panel(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """在面板中绘制设置项。"""
    prefs = get_prefs(context)

    uc.draw_section_header(layout, "API 设置", "settings")
    layout.prop(prefs, "api_endpoint", text="端点")
    layout.prop(prefs, "model_name", text="模型")

    uc.draw_section_header(layout, "上下文", "context")
    layout.prop(prefs, "context_max_objects", text="最大对象数")
    layout.prop(prefs, "context_refresh_interval", text="刷新间隔")
