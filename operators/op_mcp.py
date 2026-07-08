"""
op_mcp.py — MCP 服务器控制 Operators
=====================================
启动 / 停止 / 重启 MCP TCP 服务器。
"""

from __future__ import annotations

import bpy
from bpy.types import Operator

from ..preferences import get_prefs


class AIWORK_OT_MCPStart(Operator):
    """启动 MCP TCP 服务器"""
    bl_idname = "aiwork.mcp_start"
    bl_label = "启动 MCP 服务器"
    bl_description = "启动 TCP 服务器，允许外部 AI 工具连接并调用 Blender 工具"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        from ..mcp_server import start_server
        prefs = get_prefs(context)
        ok = start_server(host=prefs.mcp_host, port=prefs.mcp_port)
        if ok:
            self.report({'INFO'}, f"MCP 服务器已启动: {prefs.mcp_host}:{prefs.mcp_port}")
        else:
            self.report({'ERROR'}, f"启动失败，端口 {prefs.mcp_port} 可能被占用")
        return {'FINISHED'}


class AIWORK_OT_MCPStop(Operator):
    """停止 MCP TCP 服务器"""
    bl_idname = "aiwork.mcp_stop"
    bl_label = "停止 MCP 服务器"
    bl_description = "停止 TCP 服务器"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        from ..mcp_server import stop_server
        stop_server()
        self.report({'INFO'}, "MCP 服务器已停止")
        return {'FINISHED'}


class AIWORK_OT_MCPRestart(Operator):
    """重启 MCP TCP 服务器"""
    bl_idname = "aiwork.mcp_restart"
    bl_label = "重启 MCP 服务器"
    bl_description = "重启 TCP 服务器"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        from ..mcp_server import start_server, stop_server
        prefs = get_prefs(context)
        stop_server()
        ok = start_server(host=prefs.mcp_host, port=prefs.mcp_port)
        if ok:
            self.report({'INFO'}, f"MCP 服务器已重启: {prefs.mcp_host}:{prefs.mcp_port}")
        else:
            self.report({'ERROR'}, "重启失败")
        return {'FINISHED'}
