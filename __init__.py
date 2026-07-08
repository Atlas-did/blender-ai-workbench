"""
AIWork — Blender AI 工作台插件入口
====================================
这是 Blender 加载插件时第一个执行的文件。
负责注册/注销所有子模块：偏好设置、面板、操作符、UI、服务等。
"""

import importlib
import logging
import sys
import traceback

import bpy
from bpy.props import StringProperty

# ---------------------------------------------------------------------------
# bl_info — Blender 识别插件的入口元信息（必须在 __init__.py 中）
# ---------------------------------------------------------------------------
bl_info = {
    "name": "AIWork — AI 工作台",
    "description": (
        "Blender AI 工作台：内置聊天面板、场景上下文采集、"
        "工具调用、确认机制、会话管理。把 Blender 变成 AI IDE 工作台。"
    ),
    "author": "AIWork Project",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport → Sidebar → AIWork",
    "doc_url": "",
    "tracker_url": "",
    "category": "3D View",
    "support": "COMMUNITY",
}

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 安全的子模块导入 — 任一模块导入失败都会打印完整 traceback
# ---------------------------------------------------------------------------

def _safe_import(module_name: str) -> None:
    """安全导入子模块，失败时打印详细错误但不阻止其他模块加载。"""
    try:
        importlib.import_module(module_name)
    except Exception:
        log.error("导入模块失败: %s", module_name)
        log.error(traceback.format_exc())
        # 把错误详情写入一个文件，方便调试
        _write_import_error(module_name, traceback.format_exc())


def _write_import_error(module_name: str, tb: str) -> None:
    """把导入错误写入临时文件，方便在 Blender 外查看。"""
    try:
        import os
        debug_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "AIWork-debug-summary.md"
        )
        with open(debug_path, "w", encoding="utf-8") as f:
            f.write(f"# AIWork Import Error\n\nModule: `{module_name}`\n\n```\n{tb}\n```\n")
    except Exception:
        pass


# 按依赖顺序导入所有子模块

# 0. 基础模块（无 Blender 依赖）
_safe_import(f"{__package__}.schemas")
_safe_import(f"{__package__}.settings")
_safe_import(f"{__package__}.state")

# 1. 数据层
_safe_import(f"{__package__}.storage")

# 2. 偏好设置
_safe_import(f"{__package__}.preferences")

# 3. 上下文采集
_safe_import(f"{__package__}.context_scene")
_safe_import(f"{__package__}.context_project")
_safe_import(f"{__package__}.context_builder")

# 4. 工具
_safe_import(f"{__package__}.tools_registry")

# 5. 执行器
_safe_import(f"{__package__}.executor")

# 6. API / MCP 通信
_safe_import(f"{__package__}.api_client")
_safe_import(f"{__package__}.mcp_client")
_safe_import(f"{__package__}.mcp_server")

# 7. 安全 & 审计
_safe_import(f"{__package__}.security")
_safe_import(f"{__package__}.audit")

# 8. 工具扩展
_safe_import(f"{__package__}.tools_scene")
_safe_import(f"{__package__}.tools_python")
_safe_import(f"{__package__}.tools_files")

# 9. UI
_safe_import(f"{__package__}.ui.ui_common")
_safe_import(f"{__package__}.ui.ui_chat")
_safe_import(f"{__package__}.ui.ui_history")
_safe_import(f"{__package__}.ui.ui_context")
_safe_import(f"{__package__}.ui.ui_logs")
_safe_import(f"{__package__}.ui.ui_settings")

# 10. Panels
_safe_import(f"{__package__}.panels.panel_chat")

# 11. Operators
_safe_import(f"{__package__}.operators.op_chat_send")
_safe_import(f"{__package__}.operators.op_chat_clear")
_safe_import(f"{__package__}.operators.op_refresh_context")
_safe_import(f"{__package__}.operators.op_tool_confirm")
_safe_import(f"{__package__}.operators.op_tool_execute")
_safe_import(f"{__package__}.operators.op_open_file")
_safe_import(f"{__package__}.operators.op_update")
_safe_import(f"{__package__}.operators.op_mcp")

# 12. Services（骨架）
_safe_import(f"{__package__}.services.service_bridge")
_safe_import(f"{__package__}.services.service_worker")
_safe_import(f"{__package__}.services.service_events")
_safe_import(f"{__package__}.services.service_stream")

# ---------------------------------------------------------------------------
# 动态属性注册（挂在 WindowManager 上的运行时属性）
# ---------------------------------------------------------------------------

def _register_window_manager_props() -> None:
    """注册挂在 WindowManager 上的动态属性。"""
    bpy.types.WindowManager.aiwork_chat_input = StringProperty(
        name="aiwork_chat_input",
        description="AIWork 聊天输入框文本",
        default="",
        maxlen=4000,
        options={'SKIP_SAVE'},  # 不保存到 blend 文件
    )


def _unregister_window_manager_props() -> None:
    """注销 WindowManager 上的动态属性。"""
    if hasattr(bpy.types.WindowManager, "aiwork_chat_input"):
        del bpy.types.WindowManager.aiwork_chat_input


# ---------------------------------------------------------------------------
# 辅助：从 sys.modules 获取已导入的子模块
# ---------------------------------------------------------------------------

def _mod(name: str):
    """返回已导入的子模块，若导入失败则返回 None。"""
    full = f"{__package__}.{name}"
    return sys.modules.get(full)


# ---------------------------------------------------------------------------
# 待注册的类列表
# ---------------------------------------------------------------------------

_registerable_classes: list[type] = []


def _collect_classes() -> None:
    """收集所有需要向 Blender 注册的类。"""
    _registerable_classes.clear()

    # -- 偏好设置 --
    if m := _mod("preferences"):
        _registerable_classes.append(m.AIWorkPreferences)

    # -- Panels --
    if m := _mod("panels.panel_chat"):
        _registerable_classes.append(m.AIWORK_PT_Chat)
        _registerable_classes.append(m.AIWORK_PT_ChatContext)
        _registerable_classes.append(m.AIWORK_PT_ChatLogs)

    # -- Operators --
    if m := _mod("operators.op_chat_send"):
        _registerable_classes.append(m.AIWORK_OT_ChatSend)
        _registerable_classes.append(m.AIWORK_OT_ChatRetry)
    if m := _mod("operators.op_chat_clear"):
        _registerable_classes.append(m.AIWORK_OT_ChatClear)
        _registerable_classes.append(m.AIWORK_OT_ChatNewSession)
    if m := _mod("operators.op_refresh_context"):
        _registerable_classes.append(m.AIWORK_OT_RefreshContext)
    if m := _mod("operators.op_tool_confirm"):
        _registerable_classes.append(m.AIWORK_OT_ConfirmAllTools)
        _registerable_classes.append(m.AIWORK_OT_CancelAllTools)
    if m := _mod("operators.op_tool_execute"):
        _registerable_classes.append(m.AIWORK_OT_ToolExecute)
    if m := _mod("operators.op_open_file"):
        _registerable_classes.append(m.AIWORK_OT_OpenFile)
    if m := _mod("operators.op_update"):
        _registerable_classes.append(m.AIWORK_OT_CheckUpdate)
        _registerable_classes.append(m.AIWORK_OT_GitLog)
    if m := _mod("operators.op_mcp"):
        _registerable_classes.append(m.AIWORK_OT_MCPStart)
        _registerable_classes.append(m.AIWORK_OT_MCPStop)
        _registerable_classes.append(m.AIWORK_OT_MCPRestart)


# ---------------------------------------------------------------------------
# register / unregister
# ---------------------------------------------------------------------------

def register() -> None:
    """插件注册入口。"""
    log.info("=" * 50)
    log.info("AIWork 插件启动中…")

    # 1. 注册 WindowManager 属性
    try:
        _register_window_manager_props()
    except Exception:
        log.error("注册 WindowManager 属性失败:\n%s", traceback.format_exc())

    # 2. 收集并注册所有 Blender 类
    _collect_classes()
    for cls in _registerable_classes:
        try:
            bpy.utils.register_class(cls)
            log.debug("  注册类: %s", cls.__name__)
        except Exception:
            log.error("注册类 %s 失败:\n%s", cls.__name__, traceback.format_exc())

    # 3. 注册内置工具
    if m := _mod("tools_registry"):
        m.register_builtin_tools()
        tool_count = len(m.list_tool_names())
    else:
        tool_count = 0

    # 4. 加载历史会话
    if m := _mod("storage"):
        try:
            sessions = m.load_sessions()
            if sessions:
                st = _mod("state")
                if st:
                    st.get_state().sessions = sessions
                    st.get_state().current_session = sessions[-1]
                    log.info("已恢复 %d 个历史会话", len(sessions))
        except Exception:
            log.error("加载历史会话失败:\n%s", traceback.format_exc())

    # 5. 自动启动 MCP 服务器（如果配置了）
    if m := _mod("preferences"):
        try:
            prefs = m.get_prefs()
            if prefs.mcp_enabled and prefs.mcp_auto_start:
                srv_m = _mod("mcp_server")
                if srv_m:
                    srv_m.start_server(host=prefs.mcp_host, port=prefs.mcp_port)
                    log.info("MCP 服务器自动启动")
        except Exception:
            log.error("MCP 服务器自动启动失败:\n%s", traceback.format_exc())

    log.info(
        "AIWork 插件已启动 — %d 个类, %d 个工具",
        len(_registerable_classes), tool_count,
    )
    log.info("=" * 50)


def unregister() -> None:
    """插件注销入口。"""
    log.info("AIWork 插件正在关闭…")

    # 0. 停止 MCP 服务器
    try:
        srv_m = _mod("mcp_server")
        if srv_m:
            srv_m.stop_server()
    except Exception:
        pass

    # 1. 保存当前会话
    st = _mod("state")
    storage_mod = _mod("storage")
    if st and storage_mod:
        try:
            sessions = st.get_state().sessions
            if sessions:
                storage_mod.save_sessions(sessions)
        except Exception:
            log.error("保存会话失败:\n%s", traceback.format_exc())

    # 2. 注销所有 Blender 类（逆序）
    for cls in reversed(_registerable_classes):
        try:
            bpy.utils.unregister_class(cls)
            log.debug("  注销类: %s", cls.__name__)
        except Exception:
            log.error("注销类 %s 失败:\n%s", cls.__name__, traceback.format_exc())

    _registerable_classes.clear()

    # 3. 清理 WindowManager 属性
    try:
        _unregister_window_manager_props()
    except Exception:
        log.error("清理 WindowManager 属性失败:\n%s", traceback.format_exc())

    log.info("AIWork 插件已关闭。")


# ---------------------------------------------------------------------------
# 开发用热重载
# ---------------------------------------------------------------------------
# 在 Blender Scripting 工作区执行：
#
#   import importlib, aiwork
#   aiwork.unregister()
#   for mod in [aiwork, aiwork.schemas, aiwork.settings, aiwork.state,
#                aiwork.storage, aiwork.preferences,
#                aiwork.context_scene, aiwork.context_project, aiwork.context_builder,
#                aiwork.tools_registry, aiwork.executor,
#                aiwork.ui.ui_common, aiwork.ui.ui_chat,
#                aiwork.panels.panel_chat,
#                aiwork.operators.op_chat_send, aiwork.operators.op_chat_clear,
#                aiwork.operators.op_refresh_context, aiwork.operators.op_tool_confirm]:
#       importlib.reload(mod)
#   aiwork.register()
