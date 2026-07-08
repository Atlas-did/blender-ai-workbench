"""
ui_common.py — UI 公共组件与样式帮助函数
=========================================
所有 UI 模块共享的绘制工具：分隔线、图标映射、颜色常量、消息气泡等。
"""

from __future__ import annotations

import bpy


# ---------------------------------------------------------------------------
# 颜色常量（Blender 主题兼容）
# ---------------------------------------------------------------------------
# 使用 Blender 内置主题色，自动适配明暗主题

def _theme() -> bpy.types.Theme:
    return bpy.context.preferences.themes[0]


def COLOR_TEXT() -> tuple[float, float, float, float]:
    """正文颜色。"""
    return tuple(_theme().user_interface.wcol_text.text)  # type: ignore[return-value]


def COLOR_USER_BUBBLE() -> tuple[float, float, float, float]:
    """用户消息气泡底色。"""
    t = _theme().user_interface
    return (t.wcol_tool.inner[0], t.wcol_tool.inner[1], t.wcol_tool.inner[2], 0.35)


def COLOR_AI_BUBBLE() -> tuple[float, float, float, float]:
    """AI 消息气泡底色。"""
    t = _theme().user_interface
    return (t.wcol_pie_menu.inner[0], t.wcol_pie_menu.inner[1], t.wcol_pie_menu.inner[2], 0.25)


def COLOR_TOOL_CARD() -> tuple[float, float, float, float]:
    """工具调用卡片底色。"""
    t = _theme().user_interface
    return (t.wcol_box.inner[0], t.wcol_box.inner[1], t.wcol_box.inner[2], 0.5)


def COLOR_WARN() -> tuple[float, float, float, float]:
    return (1.0, 0.65, 0.0, 1.0)


def COLOR_ERROR() -> tuple[float, float, float, float]:
    return (1.0, 0.25, 0.25, 1.0)


def COLOR_OK() -> tuple[float, float, float, float]:
    return (0.3, 0.85, 0.3, 1.0)


def COLOR_MUTED() -> tuple[float, float, float, float]:
    """次要文字颜色。"""
    base = COLOR_TEXT()
    return (base[0], base[1], base[2], 0.45)


# ---------------------------------------------------------------------------
# 图标映射
# ---------------------------------------------------------------------------

ICON_MAP = {
    "user": "USER",
    "ai": "OUTLINER_OB_LIGHTPROBE",      # 小灯泡代表 AI
    "tool": "TOOL_SETTINGS",
    "send": "EXPORT",
    "chat": "TEXT",
    "clear": "TRASH",
    "refresh": "FILE_REFRESH",
    "confirm": "CHECKMARK",
    "cancel": "X",
    "error": "ERROR",
    "warn": "ERROR",                      # Blender 无专门 warning 图标
    "file": "FILE",
    "folder": "FILE_FOLDER",
    "scene": "SCENE_DATA",
    "settings": "PREFERENCES",
    "log": "TEXT",
    "context": "INFO",
    "retry": "FILE_REFRESH",
    "pending": "SORTTIME",
    "running": "PLAY",
    "done": "CHECKMARK",
    "failed": "X",
}


def icon(key: str) -> str:
    """取图标 ID，不存在的 key 返回空字符串（Blender 容错）。"""
    return ICON_MAP.get(key, "DOT")


# ---------------------------------------------------------------------------
# 布局辅助
# ---------------------------------------------------------------------------

def draw_separator(layout: bpy.types.UILayout, text: str = "") -> None:
    """画一条带可选文字的视觉分隔线。"""
    row = layout.row(align=True)
    if text:
        row.label(text=text, icon="DISCLOSURE_TRI_RIGHT")
    row.separator(factor=0.6)
    row.separator_spacer()


def draw_section_header(
    layout: bpy.types.UILayout, text: str, icon_key: str = "", collapsed: bool = False
) -> None:
    """画一个区域标题行。"""
    row = layout.row(align=True)
    row.label(text=text, icon=icon(icon_key))
    row.separator_spacer()


def draw_status_chip(
    layout: bpy.types.UILayout,
    label: str,
    value: str,
    icon_key: str = "",
    *,
    alert: bool = False,
) -> None:
    """画一个轻量状态胶囊。"""
    row = layout.row(align=True)
    row.alert = alert
    row.label(text=label, icon=icon(icon_key))
    row.separator_spacer()
    row.label(text=value)


def draw_action_bar(layout: bpy.types.UILayout, actions: list[tuple[str, str, str]]) -> None:
    """绘制一组紧凑操作按钮。"""
    row = layout.row(align=True)
    for op_id, text, icon_key in actions:
        row.operator(op_id, text=text, icon=icon(icon_key))


def draw_info_panel(layout: bpy.types.UILayout, title: str, subtitle: str = "", icon_key: str = "") -> bpy.types.UILayout:
    """绘制一个带标题的卡片式信息区域。"""
    box = layout.box()
    header = box.row(align=True)
    header.label(text=title, icon=icon(icon_key))
    if subtitle:
        header.separator_spacer()
        header.label(text=subtitle)
    return box


def draw_labeled_row(
    layout: bpy.types.UILayout, label: str, value: str, icon_key: str = ""
) -> None:
    """画 label: value 形式的行。"""
    row = layout.row(align=True)
    row.label(text=f"{label}:", icon=icon(icon_key))
    row.label(text=value)


def draw_multiline_text(layout: bpy.types.UILayout, text: str, max_width: int = 60) -> None:
    """在 Blender UI 中绘制多行文本（自动按宽度折行）。"""
    col = layout.column(align=True)
    for line in _wrap_text(text, max_width):
        col.label(text=line)


def _wrap_text(text: str, width: int) -> list[str]:
    """简单按字符宽度折行。"""
    if not text:
        return [""]
    lines = []
    for para in text.split("\n"):
        while len(para) > width:
            # 尝试在空格处断行
            split_at = para.rfind(" ", 0, width)
            if split_at == -1:
                split_at = width
            lines.append(para[:split_at])
            para = para[split_at:].lstrip()
        if para or not lines:
            lines.append(para)
    return lines


# ---------------------------------------------------------------------------
# 消息卡片绘制
# ---------------------------------------------------------------------------

def draw_user_message(layout: bpy.types.UILayout, content: str, timestamp: str = "") -> None:
    """绘制一条用户消息气泡。"""
    box = layout.box()
    header = box.row(align=True)
    header.label(text="你", icon=icon("user"))
    header.separator_spacer()
    if timestamp:
        header.label(text=timestamp, icon="TIME")
    if timestamp:
        box.separator(factor=0.2)
    draw_multiline_text(box, content)


def draw_ai_message(
    layout: bpy.types.UILayout, content: str, timestamp: str = "", is_streaming: bool = False
) -> None:
    """绘制一条 AI 回复气泡。"""
    box = layout.box()
    header = box.row(align=True)
    header.label(text="AI 助手", icon=icon("ai"))
    header.separator_spacer()
    if timestamp:
        header.label(text=timestamp, icon="TIME")
    if is_streaming:
        header.label(text="流式接收中…", icon=icon("pending"))
    box.separator(factor=0.2)
    draw_multiline_text(box, content)


def draw_tool_call_card(
    layout: bpy.types.UILayout,
    tool_name: str,
    arguments: dict,
    status: str = "pending",
    result: str = "",
) -> None:
    """绘制一次工具调用的卡片。"""
    box = layout.box()
    box.alert = status in ("pending", "failed")

    # 标题行：工具名 + 状态
    row = box.row(align=True)
    row.label(text=tool_name, icon=icon("tool"))
    row.separator_spacer()

    status_icon = icon(status)
    status_label = {
        "pending": "等待确认",
        "approved": "已批准",
        "running": "执行中…",
        "done": "完成",
        "failed": "失败",
        "cancelled": "已取消",
    }.get(status, status)
    row.label(text=status_label, icon=status_icon)

    # 参数摘要
    if arguments:
        arg_box = box.box()
        arg_box.scale_y = 0.95
        for key, val in arguments.items():
            val_str = str(val)
            if len(val_str) > 60:
                val_str = val_str[:57] + "…"
            arg_box.row(align=True).label(text=f"  {key}: {val_str}")

    # 结果（仅完成/失败时展示）
    if result and status in ("done", "failed"):
        result_box = box.box()
        result_box.scale_y = 0.95
        draw_multiline_text(result_box, str(result))


def draw_empty_state(layout: bpy.types.UILayout, text: str = "暂无消息") -> None:
    """绘制空状态占位。"""
    col = layout.column(align=True)
    col.separator(factor=1.2)
    row = col.row(align=True)
    row.alignment = "CENTER"
    row.label(text=text, icon=icon("chat"))
    col.separator(factor=1.2)
