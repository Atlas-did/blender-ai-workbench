"""
AIWork — Blender AI 工作台
===========================
Blender AI 工作台：内置聊天面板、场景上下文采集、
工具调用、确认机制、会话管理、MCP 服务器、Provider 多模型支持。
"""

bl_info = {
    "name": "AIWork — AI 工作台",
    "description": (
        "Blender AI 工作台：内置聊天面板、场景上下文采集、"
        "工具调用、确认机制、会话管理、MCP 服务器。"
    ),
    "author": "AIWork Project",
    "version": (0, 2, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport → Sidebar → AIWork",
    "doc_url": "https://github.com/Atlas-did/blender-ai-workbench",
    "tracker_url": "",
    "category": "3D View",
    "support": "COMMUNITY",
}

import importlib
import logging
import sys
import traceback

import bpy

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 子模块列表
# ---------------------------------------------------------------------------

_submodules = [
    "schemas", "settings", "state", "storage",
    "property",
    "providers",
    "preferences",
    "context_scene", "context_project", "context_builder",
    "tools_registry", "tools_scene", "tools_files", "tools_python",
    "executor",
    "api_client", "mcp_client", "mcp_server",
    "security", "audit",
    "ui.ui_common", "ui.ui_chat", "ui.ui_history", "ui.ui_context", "ui.ui_logs", "ui.ui_settings",
    "panels.panel_chat",
    "operators.op_chat_send", "operators.op_chat_clear",
    "operators.op_refresh_context", "operators.op_tool_confirm",
    "operators.op_tool_execute", "operators.op_open_file",
    "operators.op_update", "operators.op_mcp",
    "services.service_bridge", "services.service_worker",
    "services.service_events", "services.service_stream",
]


def _safe_import(name: str):
    """安全导入子模块，失败不阻止其他模块。"""
    full = f"{__package__}.{name}"
    try:
        importlib.import_module(full)
    except Exception:
        log.error("导入 %s 失败:\n%s", full, traceback.format_exc())


def _mod(name: str):
    return sys.modules.get(f"{__package__}.{name}")


# ---------------------------------------------------------------------------
# 待注册的 Blender 类
# ---------------------------------------------------------------------------

_registerable_classes: list[type] = []


def _collect_classes():
    _registerable_classes.clear()

    # 偏好设置
    if m := _mod("preferences"):
        _registerable_classes.append(m.AIWorkPreferences)

    # 属性组
    if m := _mod("property"):
        _registerable_classes.append(m.AIWorkMessageItem)
        _registerable_classes.append(m.AIWorkSessionItem)
        _registerable_classes.append(m.AIWorkSceneProperty)

    # 面板
    if m := _mod("panels.panel_chat"):
        _registerable_classes.append(m.AIWORK_PT_Chat)
        _registerable_classes.append(m.AIWORK_PT_ChatContext)
        _registerable_classes.append(m.AIWORK_PT_ChatLogs)

    # 操作符
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
# 动态属性
# ---------------------------------------------------------------------------

def _register_window_manager_props():
    bpy.types.WindowManager.aiwork_chat_input = bpy.props.StringProperty(
        name="aiwork_chat_input", default="", maxlen=4000,
        options={'SKIP_SAVE'},
    )


def _unregister_window_manager_props():
    if hasattr(bpy.types.WindowManager, "aiwork_chat_input"):
        del bpy.types.WindowManager.aiwork_chat_input


# ---------------------------------------------------------------------------
# register / unregister
# ---------------------------------------------------------------------------

def register():
    log.info("=" * 50)
    log.info("AIWork 插件启动中…")

    # 0. 导入所有子模块
    for name in _submodules:
        _safe_import(name)

    # 1. 注册 WindowManager 属性
    try:
        _register_window_manager_props()
    except Exception:
        log.error("注册 WM 属性失败:\n%s", traceback.format_exc())

    # 2. 注册 Blender 类
    _collect_classes()
    for cls in _registerable_classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            log.error("注册类 %s 失败:\n%s", cls.__name__, traceback.format_exc())

    # 3. Scene property 指针
    if m := _mod("property"):
        try:
            bpy.types.Scene.aiwork_property = bpy.props.PointerProperty(
                type=m.AIWorkSceneProperty
            )
        except Exception:
            log.error("注册 Scene.aiwork_property 失败:\n%s", traceback.format_exc())

    # 4. Provider 注册
    if m := _mod("providers"):
        try:
            m.register()
        except Exception:
            log.error("Provider 注册失败:\n%s", traceback.format_exc())

    # 5. 注册内置工具
    if m := _mod("tools_registry"):
        try:
            m.register_builtin_tools()
            tool_count = len(m.list_tool_names())
        except Exception:
            tool_count = 0
    else:
        tool_count = 0

    # 6. 启动事件监听
    if m := _mod("services.service_events"):
        try:
            m.register()
        except Exception:
            log.error("事件监听启动失败:\n%s", traceback.format_exc())

    # 7. 加载历史会话
    storage_m = _mod("storage")
    state_m = _mod("state")
    if storage_m and state_m:
        try:
            sessions = storage_m.load_sessions()
            if sessions:
                state_m.get_state().sessions = sessions
                state_m.get_state().current_session = sessions[-1]
                log.info("已恢复 %d 个历史会话", len(sessions))
        except Exception:
            log.error("加载会话失败:\n%s", traceback.format_exc())

    # 8. 自动启动 MCP
    pref_m = _mod("preferences")
    if pref_m:
        try:
            prefs = pref_m.get_prefs()
            if prefs.mcp_enabled and prefs.mcp_auto_start:
                srv_m = _mod("mcp_server")
                if srv_m:
                    srv_m.start_server(host="localhost", port=prefs.mcp_port)
        except Exception:
            pass

    log.info("AIWork 已启动 — %d 个类, %d 个工具",
             len(_registerable_classes), tool_count)
    log.info("=" * 50)


def unregister():
    log.info("AIWork 正在关闭…")

    # 0. 停止 MCP
    try:
        m = _mod("mcp_server")
        if m: m.stop_server()
    except Exception: pass

    # 1. 停止事件监听
    try:
        m = _mod("services.service_events")
        if m: m.unregister()
    except Exception: pass

    # 2. 保存会话
    try:
        st = _mod("state")
        sm = _mod("storage")
        if st and sm:
            sessions = st.get_state().sessions
            if sessions: sm.save_sessions(sessions)
    except Exception: pass

    # 3. 清理工具
    try:
        m = _mod("tools_registry")
        if m:
            for name in list(m.list_tool_names()):
                m.unregister_tool(name)
    except Exception: pass

    # 4. 注销 Blender 类（逆序）
    for cls in reversed(_registerable_classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception: pass
    _registerable_classes.clear()

    # 5. 删除 Scene property
    try:
        del bpy.types.Scene.aiwork_property
    except Exception: pass

    # 6. 清理 WM 属性
    try:
        _unregister_window_manager_props()
    except Exception: pass

    # 7. 清理 Provider
    try:
        m = _mod("providers")
        if m: m.unregister()
    except Exception: pass

    log.info("AIWork 已关闭。")
