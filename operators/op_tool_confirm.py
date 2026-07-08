"""
op_tool_confirm.py — 工具确认 / 取消 Operator
==============================================
处理高风险工具的确认与取消逻辑。
用户确认后自动把工具结果发回 AI 继续对话。
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from .. import state
from ..executor import execute_pending_tools
from ..preferences import get_prefs
from ..schemas import Role, ToolCallStatus
from ..operators.op_chat_send import _continue_conversation, _tag_redraw


class AIWORK_OT_ConfirmAllTools(Operator):
    """确认所有待执行的工具调用"""
    bl_idname = "aiwork.confirm_all_tools"
    bl_label = "确认全部工具"
    bl_description = "批准所有待确认的工具调用并执行，然后自动把结果发回 AI"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        pending = state.get_state().pending_tool_calls
        if not pending:
            self.report({'INFO'}, "没有待确认的工具")
            return {'CANCELLED'}

        for tc in pending:
            tc.status = ToolCallStatus.APPROVED

        count = len(pending)
        results = execute_pending_tools()
        self.report({'INFO'}, f"已批准并执行 {len(results)} / {count} 个工具调用")

        # 工具执行完毕 → 继续对话，把结果发回 AI
        session = state.get_current_session()
        if session and session.messages:
            # 找到最后一条 assistant 消息（包含 tool_calls 的那条）
            placeholder = None
            for m in reversed(session.messages):
                if m.role == Role.ASSISTANT and m.tool_calls:
                    placeholder = m
                    break

            if placeholder:
                state.set_processing(True)
                prefs = get_prefs(context)
                _continue_conversation(prefs, placeholder)
                # 启动 timer 轮询后续结果
                from ..operators.op_chat_send import AIWORK_OT_ChatSend
                bpy.app.timers.register(AIWORK_OT_ChatSend._poll_stream, first_interval=0.1)
            else:
                state.set_processing(False)

        _tag_redraw()
        return {'FINISHED'}


class AIWORK_OT_CancelAllTools(Operator):
    """取消所有待执行的工具调用"""
    bl_idname = "aiwork.cancel_all_tools"
    bl_label = "取消全部工具"
    bl_description = "取消所有待确认的工具调用"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        pending = state.get_state().pending_tool_calls
        if not pending:
            self.report({'INFO'}, "没有待取消的工具")
            return {'CANCELLED'}

        for tc in pending:
            tc.status = ToolCallStatus.CANCELLED

        count = len(pending)
        state.clear_pending_tools()
        state.set_processing(False)
        state.get_state().tool_chain_depth = 0
        _tag_redraw()
        self.report({'INFO'}, f"已取消 {count} 个工具调用")
        return {'FINISHED'}
