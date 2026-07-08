"""
ui_logs.py — 日志与执行反馈 UI
===============================
底部日志面板的 UI 绘制。
"""

from __future__ import annotations

import bpy

from .. import state
from . import ui_common as uc


def draw_logs_panel(layout: bpy.types.UILayout) -> None:
	"""绘制现代卡片式日志视图。"""
	box = uc.draw_info_panel(layout, "运行日志", "最近错误与会话概览", "log")

	last_error = state.get_state().last_error
	if last_error:
		err = box.box()
		err.alert = True
		err.row(align=True).label(text="最近错误", icon=uc.icon("error"))
		err.separator(factor=0.2)
		uc.draw_multiline_text(err, last_error)
	else:
		uc.draw_status_chip(box, "最近错误", "无", "done")

	session = state.get_current_session()
	if session:
		uc.draw_status_chip(box, "当前会话", session.title, "chat")
		uc.draw_status_chip(box, "消息数", f"{len(session.messages)} 条", "chat")
		uc.draw_status_chip(box, "创建时间", _fmt_time(session.created_at), "pending")
		uc.draw_status_chip(box, "更新时间", _fmt_time(session.updated_at), "refresh")
	else:
		uc.draw_empty_state(box, "暂无活动会话")

	footer = box.row(align=True)
	footer.operator("aiwork.chat_new_session", text="新建会话", icon="ADD")
	footer.operator("aiwork.chat_clear", text="清空", icon=uc.icon("clear"))


def _fmt_time(timestamp: float) -> str:
	import time
	return time.strftime("%Y-%m-%d %H:%M", time.localtime(timestamp))
