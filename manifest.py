"""
AIWork — Blender AI 工作台插件
=================================
把 Blender 做成 AI 辅助的 3D 工作台：
用户提问 → 采集场景上下文 → AI 分析 → 调用工具 → 确认执行 → 返回结果。

bl_info 是 Blender 识别插件的入口元信息。
"""

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
