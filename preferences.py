"""
preferences.py — 插件偏好设置
==============================
Blender 插件偏好设置面板。用户在 Edit → Preferences → Add-ons → AIWork 中配置。
包含 API 连接、MCP 服务器、模型参数、上下文采集选项等。
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty
from bpy.types import AddonPreferences

from .settings import (
    ADDON_LABEL,
    DEFAULT_API_ENDPOINT,
    DEFAULT_API_KEY,
    DEFAULT_CONTEXT_INCLUDE_FILEPATH,
    DEFAULT_CONTEXT_INCLUDE_RENDER,
    DEFAULT_CONTEXT_INCLUDE_WORLD,
    DEFAULT_CONTEXT_MAX_OBJECTS,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MCP_ENABLED,
    DEFAULT_MCP_SERVER_ADDRESS,
    DEFAULT_MODEL_NAME,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_TEMPERATURE,
    CONTEXT_REFRESH_INTERVAL,
)


class AIWorkPreferences(AddonPreferences):
    """AIWork 插件偏好设置。"""
    bl_idname = "aiwork"

    # ------------------------------------------------------------------
    # API 连接
    # ------------------------------------------------------------------
    api_endpoint: StringProperty(
        name="API 地址",
        description="LLM API 端点 (OpenAI 兼容格式)",
        default=DEFAULT_API_ENDPOINT,
    )

    api_key: StringProperty(
        name="API Key",
        description="API 密钥（本地模型如 Ollama 可留空）",
        default=DEFAULT_API_KEY,
        subtype='PASSWORD',
    )

    model_name: StringProperty(
        name="模型名称",
        description="使用的 LLM 模型 ID",
        default=DEFAULT_MODEL_NAME,
    )

    # ------------------------------------------------------------------
    # 生成参数
    # ------------------------------------------------------------------
    max_tokens: IntProperty(
        name="最大 Token 数",
        description="单次回复最大输出 token 数",
        default=DEFAULT_MAX_TOKENS,
        min=64,
        max=65536,
        soft_max=16384,
    )

    temperature: FloatProperty(
        name="Temperature",
        description="生成随机性（越高越不固定，越低越确定）",
        default=DEFAULT_TEMPERATURE,
        min=0.0,
        max=2.0,
        step=0.05,
    )

    request_timeout: IntProperty(
        name="请求超时 (秒)",
        description="单次 HTTP 请求的超时时间",
        default=DEFAULT_REQUEST_TIMEOUT,
        min=5,
        max=300,
    )

    # ------------------------------------------------------------------
    # MCP 服务器设置
    # ------------------------------------------------------------------
    mcp_enabled: BoolProperty(
        name="启用 MCP 服务器",
        description="启动 TCP 服务器，让外部 AI 工具（Claude Code / VS Code）直接调用 Blender 工具",
        default=DEFAULT_MCP_ENABLED,
    )

    mcp_host: StringProperty(
        name="MCP 监听地址",
        description="MCP 服务器绑定的地址",
        default="localhost",
    )

    mcp_port: IntProperty(
        name="MCP 端口",
        description="MCP 服务器监听端口",
        default=9876,
        min=1024,
        max=65535,
    )

    mcp_auto_start: BoolProperty(
        name="插件加载时自动启动 MCP",
        description="启用插件时自动启动 MCP 服务器",
        default=False,
    )

    # ------------------------------------------------------------------
    # 上下文采集
    # ------------------------------------------------------------------
    context_max_objects: IntProperty(
        name="最多上报对象数",
        description="上下文采集时最多包含的场景对象数量",
        default=DEFAULT_CONTEXT_MAX_OBJECTS,
        min=5,
        max=500,
    )

    context_include_world: BoolProperty(
        name="采集世界/环境信息",
        default=DEFAULT_CONTEXT_INCLUDE_WORLD,
    )

    context_include_render: BoolProperty(
        name="采集渲染设置",
        default=DEFAULT_CONTEXT_INCLUDE_RENDER,
    )

    context_include_filepath: BoolProperty(
        name="采集文件路径",
        default=DEFAULT_CONTEXT_INCLUDE_FILEPATH,
    )

    context_refresh_interval: FloatProperty(
        name="自动刷新间隔 (秒)",
        description="上下文自动刷新间隔，0 表示关闭自动刷新",
        default=CONTEXT_REFRESH_INTERVAL,
        min=0.0,
        max=30.0,
        step=0.5,
    )

    # ------------------------------------------------------------------
    # UI 绘制
    # ------------------------------------------------------------------

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout

        # -- 更新 --
        box = layout.box()
        box.label(text="更新", icon='URL')
        row = box.row(align=True)
        row.operator("aiwork.check_update", text="检查更新 (git pull)", icon='FILE_REFRESH')
        row.operator("aiwork.git_log", text="更新日志", icon='TEXT')

        # -- API 连接 --
        box = layout.box()
        box.label(text="API 连接（聊天面板）", icon='URL')
        box.prop(self, "api_endpoint")
        box.prop(self, "api_key")
        box.prop(self, "model_name")

        row = box.row()
        row.prop(self, "max_tokens")
        row.prop(self, "temperature")
        box.prop(self, "request_timeout")

        # -- MCP 服务器 --
        box = layout.box()
        box.label(text="MCP 服务器（外部 AI 接入）", icon='NETWORK_DRIVE')
        box.prop(self, "mcp_enabled")
        if self.mcp_enabled:
            row = box.row(align=True)
            row.prop(self, "mcp_host", text="地址")
            row.prop(self, "mcp_port", text="端口")
            box.prop(self, "mcp_auto_start", text="加载插件时自动启动")

            # MCP 状态和操作按钮
            from .mcp_server import is_running
            mcp_running = is_running()
            status_text = "🟢 运行中" if mcp_running else "🔴 已停止"
            box.label(text=f"MCP 服务器状态: {status_text}")

            row = box.row(align=True)
            if mcp_running:
                row.operator("aiwork.mcp_stop", text="停止 MCP 服务器", icon='CANCEL')
            else:
                row.operator("aiwork.mcp_start", text="启动 MCP 服务器", icon='PLAY')
            row.operator("aiwork.mcp_restart", text="重启 MCP 服务器", icon='FILE_REFRESH')

        # -- 会话管理 --
        box = layout.box()
        box.label(text="会话管理", icon='FILE_TEXT')
        row = box.row(align=True)
        row.operator("aiwork.chat_clear", text="清空当前会话", icon='TRASH')
        row.operator("aiwork.chat_new_session", text="新建会话", icon='ADD')
        row.operator("aiwork.refresh_context", text="刷新上下文", icon='FILE_REFRESH')

        # -- 上下文 --
        box = layout.box()
        box.label(text="上下文采集", icon='SCENE_DATA')
        box.prop(self, "context_max_objects")
        row = box.row()
        row.prop(self, "context_include_world")
        row.prop(self, "context_include_render")
        box.prop(self, "context_include_filepath")
        box.prop(self, "context_refresh_interval")


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def get_prefs(context: bpy.types.Context | None = None) -> AIWorkPreferences:
    """获取插件偏好设置实例。"""
    if context is None:
        context = bpy.context
    return context.preferences.addons[__package__].preferences  # type: ignore[return-value]
