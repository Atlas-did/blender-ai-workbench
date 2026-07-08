"""
op_tool_execute.py — 执行单个工具 Operator
===========================================
手动选择并执行一个已注册的工具（调试/手动操作）。
"""

from __future__ import annotations

import json
import logging

import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator

from ..tools_registry import execute_tool, get_tool, list_tool_names

log = logging.getLogger(__name__)


def _tool_items(self, context):
    """生成工具下拉列表的枚举项。"""
    items = []
    for name in list_tool_names():
        entry = get_tool(name)
        if entry:
            desc = entry["definition"].description[:60]
            risk = entry["definition"].risk_level.value
            items.append((name, f"{name} [{risk}]", desc))
    if not items:
        items.append(("__none__", "(无可用工具)", ""))
    return items


class AIWORK_OT_ToolExecute(Operator):
    """手动执行一个已注册的工具"""
    bl_idname = "aiwork.tool_execute"
    bl_label = "执行工具"
    bl_description = "手动选择并执行一个已注册的工具"
    bl_options = {'REGISTER', 'UNDO'}

    tool_name: EnumProperty(
        name="工具",
        description="选择要执行的工具",
        items=_tool_items,
    )  # type: ignore[valid-type]

    arguments_json: StringProperty(
        name="参数 (JSON)",
        description="工具参数，JSON 格式，如 {} 或 {\"name\": \"Cube\"}",
        default="{}",
    )  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        if self.tool_name == "__none__":
            self.report({'WARNING'}, "没有可用的工具")
            return {'CANCELLED'}

        # 解析参数
        try:
            args = json.loads(self.arguments_json)
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"参数 JSON 解析失败: {e}")
            return {'CANCELLED'}

        if not isinstance(args, dict):
            self.report({'ERROR'}, "参数必须是 JSON 对象 ({})")
            return {'CANCELLED'}

        # 执行工具
        try:
            result = execute_tool(self.tool_name, args)
            result_str = json.dumps(result, ensure_ascii=False, indent=2)
            self.report({'INFO'}, f"工具 '{self.tool_name}' 执行完成")
        except Exception as exc:
            result_str = f"执行失败: {exc}"
            self.report({'ERROR'}, f"工具执行出错: {exc}")

        # 显示结果弹窗
        def _draw_result(self_menu, _ctx):
            self_menu.layout.label(text=f"工具: {self.tool_name}", icon="TOOL_SETTINGS")
            self_menu.layout.separator()
            for line in result_str.split("\n"):
                self_menu.layout.label(text=line[:120])

        bpy.context.window_manager.popup_menu(_draw_result, title="工具执行结果", icon='TEXT')

        log.info("手动执行工具: %s args=%s → %s", self.tool_name, args, str(result_str)[:200])
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=450)
