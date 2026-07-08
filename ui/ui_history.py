"""
ui_history.py — 会话历史 UI
============================
显示历史会话列表，支持切换和删除。
"""

from __future__ import annotations

import bpy

from .. import state
from . import ui_common as uc


def draw_history_panel(layout: bpy.types.UILayout) -> None:
    """绘制会话历史列表。"""
    sessions = state.get_state().sessions
    current = state.get_current_session()

    if not sessions:
        box = uc.draw_info_panel(layout, "会话历史", "暂无历史会话", "chat")
        uc.draw_empty_state(box, "暂无历史会话")
        return

    box = uc.draw_info_panel(layout, "会话历史", f"共 {len(sessions)} 个会话", "chat")

    current_id = current.id if current else ""
    for sess in reversed(sessions):
        is_current = sess.id == current_id
        item = box.box()
        item.alert = is_current

        header = item.row(align=True)
        header.label(text=sess.title or "未命名会话", icon=uc.icon("done") if is_current else uc.icon("chat"))
        header.separator_spacer()
        if is_current:
            header.label(text="当前", icon=uc.icon("confirm"))

        uc.draw_status_chip(item, "消息", f"{len(sess.messages)} 条", "chat")
        uc.draw_status_chip(item, "创建", _fmt_time(sess.created_at), "pending")
        uc.draw_status_chip(item, "更新", _fmt_time(sess.updated_at), "refresh")

        if sess.context_snapshot and sess.context_snapshot.project.blend_filename:
            uc.draw_status_chip(
                item,
                "文件",
                sess.context_snapshot.project.blend_filename,
                "file",
            )

    footer = box.row(align=True)
    footer.operator("aiwork.chat_new_session", text="新建会话", icon="ADD")
    footer.operator("aiwork.chat_clear", text="清空当前", icon=uc.icon("clear"))


def _fmt_time(timestamp: float) -> str:
    import time
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
