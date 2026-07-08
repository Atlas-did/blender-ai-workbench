"""
op_chat_send.py — 发送聊天消息 Operator
=========================================
用户在输入框按下"发送"后触发。
流程：采集上下文 → 构建消息 → 调用 API → 流式更新 UI → 工具执行 → 继续对话。
"""

from __future__ import annotations

import json
import logging
import queue
import threading

import bpy
from bpy.types import Operator

from .. import state
from ..api_client import chat_completion_stream, messages_to_api, tool_def_to_api
from ..context_builder import build_system_prompt, collect_context
from ..executor import dispatch_tool_call
from ..preferences import get_prefs
from ..schemas import Message, RiskLevel, Role, ToolCall, ToolCallStatus
from ..tools_registry import get_all_definitions, get_tool
from ..ui.ui_chat import INPUT_PROP_NAME, _clear_input, _get_input_text

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 流式回复缓冲（线程安全）
# ---------------------------------------------------------------------------
_stream_queue: queue.Queue[dict] = queue.Queue()

# 工具链深度限制
MAX_TOOL_CHAIN_DEPTH = 10


def _tag_redraw() -> None:
    """强制重绘所有相关区域。"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in ('VIEW_3D', 'TEXT_EDITOR', 'PROPERTIES'):
                area.tag_redraw()


# ---------------------------------------------------------------------------
# 辅助：判断是否需要用户确认
# ---------------------------------------------------------------------------

def _tool_needs_confirmation(tool_name: str) -> bool:
    """检查工具是否需要用户确认（MEDIUM 或 HIGH 风险）。"""
    entry = get_tool(tool_name)
    if entry is None:
        return True  # 未知工具默认需要确认
    return entry["definition"].risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


# ---------------------------------------------------------------------------
# 辅助：继续对话（工具执行后把结果发回 AI）
# ---------------------------------------------------------------------------

def _continue_conversation(prefs, old_placeholder: Message) -> None:
    """工具执行完毕后，把结果发回 AI 获取最终回复。"""
    current_depth = state.get_state().tool_chain_depth
    if current_depth >= MAX_TOOL_CHAIN_DEPTH:
        log.warning("工具链深度已达上限 %d，停止继续", MAX_TOOL_CHAIN_DEPTH)
        state.set_processing(False)
        old_placeholder.content += "\n\n⚠ 工具链深度已达上限，请手动继续对话。"
        _tag_redraw()
        return

    state.get_state().tool_chain_depth = current_depth + 1

    # ★ 关键修复：创建全新的 placeholder，避免旧 tool_calls 污染
    new_placeholder = Message(role=Role.ASSISTANT, content="")
    state.add_message(new_placeholder)
    AIWORK_OT_ChatSend._stream_msg = new_placeholder

    api_messages = _build_messages_with_tool_results(prefs)
    tool_defs = get_all_definitions()
    api_tools = [tool_def_to_api(td) for td in tool_defs] if tool_defs else None

    def _call_followup() -> None:
        try:
            chat_completion_stream(
                messages=api_messages,
                model=prefs.model_name,
                endpoint=prefs.api_endpoint,
                api_key=prefs.api_key,
                max_tokens=prefs.max_tokens,
                temperature=prefs.temperature,
                tools=api_tools,
                timeout=prefs.request_timeout,
                on_token=lambda token: _stream_queue.put({"type": "token", "data": token}),
                on_tool_call=lambda tc_id, name, args: _stream_queue.put(
                    {"type": "tool_call", "data": {"id": tc_id, "name": name, "arguments": args}}
                ),
                on_done=lambda content, tcs, usage: _stream_queue.put(
                    {"type": "done", "data": {"content": content, "tool_calls": tcs, "usage": usage}}
                ),
            )
        except Exception as exc:
            _stream_queue.put({"type": "error", "data": str(exc)})

    threading.Thread(target=_call_followup, daemon=True).start()
    log.info("继续对话: tool_chain_depth=%d", state.get_state().tool_chain_depth)


def _build_messages_with_tool_results(prefs) -> list[dict]:
    """构建包含工具调用结果的 API 消息列表。"""
    from ..context_builder import build_system_prompt, collect_context

    session = state.get_current_session()
    if session is None:
        return []

    # 采集最新上下文
    snapshot = collect_context(bpy.context)
    session.context_snapshot = snapshot
    system_prompt = build_system_prompt(snapshot)

    api_messages = messages_to_api(
        _session_messages_to_dicts(),
        system_prompt=system_prompt,
    )
    return api_messages


# ---------------------------------------------------------------------------
# AIWORK_OT_ChatSend
# ---------------------------------------------------------------------------

class AIWORK_OT_ChatSend(Operator):
    """发送消息给 AI 助手"""
    bl_idname = "aiwork.chat_send"
    bl_label = "发送消息"
    bl_description = "将输入框内容发送给 AI 助手，自动采集当前 Blender 上下文"
    bl_options = {'REGISTER', 'UNDO'}

    _timer = None
    _stream_msg: Message | None = None
    _prefs = None  # 缓存偏好设置，供后续轮询使用
    _context = None  # 缓存 context

    def execute(self, context: bpy.types.Context) -> set[str]:
        text = _get_input_text(context).strip()
        if not text:
            self.report({'WARNING'}, "输入为空")
            return {'CANCELLED'}

        if state.is_processing():
            self.report({'WARNING'}, "正在处理上一条消息，请等待…")
            return {'CANCELLED'}

        # 确保有活动会话
        session = state.get_current_session()
        if session is None:
            session = state.new_session()

        # 重置工具链深度
        state.get_state().tool_chain_depth = 0

        # 1. 采集上下文
        prefs = get_prefs(context)
        snapshot = collect_context(context)
        session.context_snapshot = snapshot

        # 缓存 prefs 和 context 供后续轮询使用
        AIWORK_OT_ChatSend._prefs = prefs
        AIWORK_OT_ChatSend._context = context

        # 2. 构建 system prompt
        system_prompt = build_system_prompt(snapshot)

        # 3. 构建用户消息并入库
        msg = Message(role=Role.USER, content=text)
        state.add_message(msg)

        # 4. 清空输入框
        _clear_input(context)

        # 5. 标记处理中
        state.set_processing(True)

        # 6. 准备 API 参数
        api_messages = messages_to_api(
            _session_messages_to_dicts(),
            system_prompt=system_prompt,
        )

        # 工具定义
        tool_defs = get_all_definitions()
        api_tools = [tool_def_to_api(td) for td in tool_defs] if tool_defs else None

        # 7. 创建流式占位消息
        placeholder = Message(role=Role.ASSISTANT, content="")
        state.add_message(placeholder)
        AIWORK_OT_ChatSend._stream_msg = placeholder

        # 清空队列中的旧数据
        while not _stream_queue.empty():
            try:
                _stream_queue.get_nowait()
            except queue.Empty:
                break

        # 8. 后台线程发起 API 请求
        def _call_api() -> None:
            try:
                chat_completion_stream(
                    messages=api_messages,
                    model=prefs.model_name,
                    endpoint=prefs.api_endpoint,
                    api_key=prefs.api_key,
                    max_tokens=prefs.max_tokens,
                    temperature=prefs.temperature,
                    tools=api_tools,
                    timeout=prefs.request_timeout,
                    on_token=lambda token: _stream_queue.put({"type": "token", "data": token}),
                    on_tool_call=lambda tc_id, name, args: _stream_queue.put(
                        {"type": "tool_call", "data": {"id": tc_id, "name": name, "arguments": args}}
                    ),
                    on_done=lambda content, tcs, usage: _stream_queue.put(
                        {"type": "done", "data": {"content": content, "tool_calls": tcs, "usage": usage}}
                    ),
                )
            except Exception as exc:
                _stream_queue.put({"type": "error", "data": str(exc)})

        threading.Thread(target=_call_api, daemon=True).start()

        # 9. 启动 Blender timer 轮询结果
        bpy.app.timers.register(self._poll_stream, first_interval=0.1)
        log.info("用户消息已发送: %s…", text[:80])
        return {'FINISHED'}

    # ------------------------------------------------------------------
    # Timer 回调：轮询后台线程结果 + 更新 UI
    # ------------------------------------------------------------------

    @classmethod
    def _poll_stream(cls) -> float | None:
        """每 0.1s 由 Blender 主线程调用，从队列中取数据并更新 UI。

        Returns:
            float: 下次调用间隔（秒），返回 None 表示停止。
        """
        try:
            while True:
                item = _stream_queue.get_nowait()
                msg = cls._stream_msg

                if item["type"] == "token":
                    if msg:
                        msg.content += item["data"]
                    _tag_redraw()

                elif item["type"] == "tool_call":
                    tool_name = item["data"]["name"]
                    tool_args = item["data"]["arguments"]
                    tool_call_id = item["data"].get("id", "")  # API 返回的 tool_call_id

                    if _tool_needs_confirmation(tool_name):
                        # MEDIUM/HIGH 风险 → 加入待确认队列
                        tc = ToolCall(
                            id=tool_call_id or f"tc_{tool_name}",
                            tool_name=tool_name,
                            arguments=tool_args,
                            status=ToolCallStatus.PENDING,
                        )
                        if msg:
                            msg.tool_calls.append(tc)
                        state.add_pending_tool_call(tc)
                        log.info("工具 '%s' 等待用户确认 (风险: MEDIUM/HIGH)", tool_name)
                    else:
                        # LOW 风险 → 自动执行
                        tc = dispatch_tool_call(tool_name, tool_args, auto_confirm_low_risk=True)
                        # 使用 API 返回的 tool_call_id，确保后续对话中 ID 匹配
                        if tool_call_id:
                            tc.id = tool_call_id
                            # 同步更新 TOOL 消息中的 tool_call_id
                            session = state.get_current_session()
                            if session:
                                for m in reversed(session.messages):
                                    if m.role == Role.TOOL:
                                        for mtc in m.tool_calls:
                                            if mtc.tool_name == tool_name:
                                                mtc.id = tool_call_id
                                        break
                        if msg:
                            msg.tool_calls.append(tc)
                        log.info("工具 '%s' 自动执行完成 (风险: LOW) 结果=%s",
                                 tool_name, str(tc.result)[:80] if tc.result else tc.error)
                    _tag_redraw()

                elif item["type"] == "done":
                    if msg:
                        # 追加 AI 的纯文本内容（如果有）
                        content = item["data"].get("content", "")
                        if content and not msg.content:
                            msg.content = content

                    # 检查是否有待确认的工具
                    pending = state.get_state().pending_tool_calls
                    if pending:
                        # 有待确认工具 → 停止 timer，等待用户操作
                        log.info("流式响应完成，有 %d 个工具等待确认", len(pending))
                        return None
                    else:
                        # 没有待确认工具 → 检查是否有已执行的工具需要继续对话
                        has_executed_tools = bool(msg and msg.tool_calls)
                        if has_executed_tools:
                            # 工具已自动执行 → 继续对话获取 AI 最终回复
                            log.info("流式响应完成，工具已自动执行，继续对话…")
                            prefs = cls._prefs
                            if prefs is None:
                                prefs = get_prefs(bpy.context)
                            _continue_conversation(prefs, msg)
                            return 0.1  # 继续轮询
                        else:
                            # 纯文本回复 → 完成
                            state.set_processing(False)
                            state.get_state().tool_chain_depth = 0
                            _tag_redraw()
                            return None

                elif item["type"] == "error":
                    if msg:
                        msg.content = f"❌ 请求失败: {item['data']}"
                    state.set_processing(False)
                    state.set_last_error(item["data"])
                    state.get_state().tool_chain_depth = 0
                    _tag_redraw()
                    return None

        except queue.Empty:
            pass

        return 0.1  # 继续轮询


# ---------------------------------------------------------------------------
# AIWORK_OT_ChatRetry
# ---------------------------------------------------------------------------

class AIWORK_OT_ChatRetry(Operator):
    """重试上一条消息"""
    bl_idname = "aiwork.chat_retry"
    bl_label = "重试"
    bl_description = "重新发送上一条用户消息"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        session = state.get_current_session()
        if not session or not session.messages:
            self.report({'WARNING'}, "没有可以重试的消息")
            return {'CANCELLED'}

        # 找到最后一条用户消息
        last_user = None
        for m in reversed(session.messages):
            if m.role == Role.USER:
                last_user = m
                break

        if last_user is None:
            self.report({'WARNING'}, "没有找到用户消息")
            return {'CANCELLED'}

        # 把最后一条用户消息的文本放入输入框
        context.window_manager[INPUT_PROP_NAME] = last_user.content
        # 触发发送
        return bpy.ops.aiwork.chat_send('INVOKE_DEFAULT')


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _session_messages_to_dicts() -> list[dict]:
    """把当前会话消息转为 API 格式的 dict 列表。"""
    session = state.get_current_session()
    if session is None:
        return []

    result: list[dict] = []
    for msg in session.messages:
        if msg.role == Role.USER:
            result.append({"role": "user", "content": msg.content})
        elif msg.role == Role.ASSISTANT:
            entry: dict = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            result.append(entry)
        elif msg.role == Role.TOOL:
            # 工具结果作为 tool 角色消息
            for tc in msg.tool_calls:
                result.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tc.result, ensure_ascii=False) if tc.result else tc.error or "",
                })

    return result
