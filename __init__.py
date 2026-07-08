"""
AIWork — Blender AI 工作台
===========================
参考 BlenderAIStudio 架构，采用 register_submodule_factory 模式。
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

import bpy

# 子模块列表 — 仅包含有 register() 的包
modules = [
    "property",
    "providers",
    "services",
    "ui",
    "panels",
    "operators",
]

reg, unreg = bpy.utils.register_submodule_factory(__package__, modules)


def register():
    # 1. 注册子模块（property → providers → services → ui → panels → operators）
    reg()

    # 2. 注册 AddonPreferences（非 package，手动注册）
    from . import preferences
    try:
        bpy.utils.register_class(preferences.AIWorkPreferences)
    except Exception:
        pass

    # 3. 注册内置工具
    from . import tools_registry
    tools_registry.register_builtin_tools()

    # 4. 启动事件监听
    from .services import service_events
    try:
        service_events.register()
    except Exception:
        pass

    # 5. 加载历史会话
    from . import storage, state
    try:
        sessions = storage.load_sessions()
        if sessions:
            state.get_state().sessions = sessions
            state.get_state().current_session = sessions[-1]
    except Exception:
        pass

    # 6. 自动启动 MCP 服务器
    try:
        from . import mcp_server
        prefs = preferences.get_prefs()
        if prefs.mcp_enabled and prefs.mcp_auto_start:
            mcp_server.start_server(host="localhost", port=prefs.mcp_port)
    except Exception:
        pass


def unregister():
    # 0. 停止 MCP 服务器
    try:
        from . import mcp_server
        mcp_server.stop_server()
    except Exception:
        pass

    # 1. 注销事件监听
    try:
        from .services import service_events
        service_events.unregister()
    except Exception:
        pass

    # 2. 保存当前会话
    try:
        from . import storage, state
        sessions = state.get_state().sessions
        if sessions:
            storage.save_sessions(sessions)
    except Exception:
        pass

    # 3. 注销子模块
    unreg()

    # 4. 注销 AddonPreferences
    from . import preferences
    try:
        bpy.utils.unregister_class(preferences.AIWorkPreferences)
    except Exception:
        pass

    # 5. 清理工具注册表
    from . import tools_registry
    for name in tools_registry.list_tool_names():
        tools_registry.unregister_tool(name)
