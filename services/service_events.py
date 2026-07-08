"""
service_events.py — 事件分发与消息总线
=======================================
插件内部的事件系统：
- 消息到达事件 → UI 刷新
- 工具执行完成事件 → 结果回写
- 连接状态变更事件 → 状态指示器更新
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Iterable

import bpy
from bpy.app.handlers import persistent

from .. import state
from ..context_builder import collect_context

log = logging.getLogger(__name__)

_REGISTERED = False
_REFRESH_PENDING = False
_REFRESH_TIMER_ACTIVE = False
_PENDING_REASONS: list[str] = []
_DEBOUNCE_SECONDS = 0.25
_COOLDOWN_SECONDS = 0.5  # 两次刷新之间的最小间隔
_last_refresh_time = 0.0


def register() -> None:
	"""注册 Blender 事件处理器。"""
	global _REGISTERED
	if _REGISTERED:
		return

	handlers = bpy.app.handlers
	_add_handler(handlers.depsgraph_update_post, _on_depsgraph_update)
	_add_handler(handlers.frame_change_post, _on_frame_change_post)
	_add_handler(handlers.undo_post, _on_undo_post)
	_add_handler(handlers.redo_post, _on_redo_post)
	_add_handler(handlers.load_post, _on_load_post)
	_add_handler(handlers.save_post, _on_save_post)

	_REGISTERED = True
	log.info("AIWork 事件监听已注册")


def unregister() -> None:
	"""移除 Blender 事件处理器。"""
	global _REGISTERED, _REFRESH_PENDING, _REFRESH_TIMER_ACTIVE
	if not _REGISTERED:
		return

	handlers = bpy.app.handlers
	_remove_handler(handlers.depsgraph_update_post, _on_depsgraph_update)
	_remove_handler(handlers.frame_change_post, _on_frame_change_post)
	_remove_handler(handlers.undo_post, _on_undo_post)
	_remove_handler(handlers.redo_post, _on_redo_post)
	_remove_handler(handlers.load_post, _on_load_post)
	_remove_handler(handlers.save_post, _on_save_post)

	_PENDING_REASONS.clear()
	_REFRESH_PENDING = False
	_REFRESH_TIMER_ACTIVE = False
	_REGISTERED = False
	log.info("AIWork 事件监听已注销")


def request_context_refresh(reason: str = "scene changed") -> None:
	"""请求一次上下文刷新（会去抖合并多次事件）。"""
	if state.get_current_session() is None:
		return
	global _REFRESH_PENDING
	_PENDING_REASONS.append(reason)
	_REFRESH_PENDING = True
	_ensure_refresh_timer()


def _ensure_refresh_timer() -> None:
	global _REFRESH_TIMER_ACTIVE
	if _REFRESH_TIMER_ACTIVE:
		return
	_REFRESH_TIMER_ACTIVE = True
	bpy.app.timers.register(_flush_pending_refresh, first_interval=_DEBOUNCE_SECONDS)


def _flush_pending_refresh() -> float | None:
	global _REFRESH_PENDING, _REFRESH_TIMER_ACTIVE, _last_refresh_time
	_REFRESH_TIMER_ACTIVE = False

	if not _REFRESH_PENDING:
		return None

	# AI 处理中不刷新（工具执行会导致大量 depsgraph 事件）
	if state.is_processing():
		_REFRESH_PENDING = False
		return None

	# 冷却时间：距上次刷新不足 _COOLDOWN_SECONDS 就跳过
	import time
	now = time.time()
	if now - _last_refresh_time < _COOLDOWN_SECONDS:
		return None

	_REFRESH_PENDING = False
	_last_refresh_time = now
	reasons = _drain_reasons()

	try:
		snapshot = collect_context(bpy.context)
		signature = _snapshot_signature(snapshot)
		previous = state.get_last_context_signature()

		if signature != previous:
			session = state.get_current_session()
			if session is not None:
				session.context_snapshot = snapshot
			state.set_last_context_signature(signature)

			event_text = _build_event_text(snapshot, reasons)
			state.add_recent_event(event_text)
			log.debug("自动刷新上下文: %s", event_text)
		else:
			log.debug("上下文未变化，跳过刷新")
	except Exception as exc:
		log.exception("自动刷新上下文失败: %s", exc)

	return None


def _build_event_text(snapshot, reasons: Iterable[str]) -> str:
	reason_text = ", ".join(dict.fromkeys(r.strip() for r in reasons if r.strip()))
	s = snapshot.scene
	active = s.active_object_name or "无"
	selected = len(s.selected_objects)
	pieces = ["自动检测到 Blender 变化"]
	if reason_text:
		pieces.append(f"原因: {reason_text}")
	pieces.append(f"场景: {s.scene_name or '(未命名)'}")
	pieces.append(f"活动对象: {active}")
	pieces.append(f"选中: {selected} 个")
	pieces.append(f"帧: {s.current_frame}")
	return " | ".join(pieces)


def _snapshot_signature(snapshot) -> str:
	s = snapshot.scene
	selected = [(o.name, o.type, o.location, o.visible) for o in s.selected_objects]
	visible = [(o.name, o.type, o.location, o.visible) for o in s.visible_objects]
	raw = "\n".join([
		s.scene_name,
		s.active_object_name,
		str(s.object_count),
		str(s.current_frame),
		str(s.frame_start),
		str(s.frame_end),
		s.render_engine,
		s.world_name,
		repr(selected),
		repr(visible),
		snapshot.project.blend_filepath,
		snapshot.project.blend_filename,
		str(snapshot.project.is_saved),
	])
	return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def _drain_reasons() -> list[str]:
	reasons = list(_PENDING_REASONS)
	_PENDING_REASONS.clear()
	return reasons


@persistent
def _on_depsgraph_update(*_args) -> None:
	request_context_refresh("depsgraph update")


@persistent
def _on_frame_change_post(*_args) -> None:
	request_context_refresh("frame change")


@persistent
def _on_undo_post(*_args) -> None:
	request_context_refresh("undo")


@persistent
def _on_redo_post(*_args) -> None:
	request_context_refresh("redo")


@persistent
def _on_load_post(*_args) -> None:
	request_context_refresh("load")


@persistent
def _on_save_post(*_args) -> None:
	request_context_refresh("save")


def _add_handler(handler_list, func) -> None:
	if func not in handler_list:
		handler_list.append(func)


def _remove_handler(handler_list, func) -> None:
	while func in handler_list:
		handler_list.remove(func)
