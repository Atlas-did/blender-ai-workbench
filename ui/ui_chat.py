"""
ui_chat.py — 聊天主界面绘制
============================
绘制消息流、输入框、发送按钮、工具调用确认区。
这是 AIWork 最核心的 UI 模块。
"""

from __future__ import annotations

import bpy

from .. import state
from ..schemas import Message, Role, ToolCall, ToolCallStatus
from . import ui_common as uc


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
INPUT_PROP_NAME = "aiwork_chat_input"


# ---------------------------------------------------------------------------
# 聊天输入属性（挂在 WindowManager 上）
# ---------------------------------------------------------------------------

def _get_input_text(context: bpy.types.Context) -> str:
    """读取当前输入框文本。"""
    return context.window_manager.get(INPUT_PROP_NAME, "")


def _set_input_text(context: bpy.types.Context, text: str) -> None:
    """设置输入框文本。"""
    context.window_manager[INPUT_PROP_NAME] = text


def _clear_input(context: bpy.types.Context) -> None:
    """清空输入框。"""
    context.window_manager[INPUT_PROP_NAME] = ""


# ---------------------------------------------------------------------------
# 消息列表
# ---------------------------------------------------------------------------

def draw_messages(
    layout: bpy.types.UILayout,
    messages: list[Message],
    max_display: int = 50,
) -> None:
    """绘制消息流。

    每条消息根据角色用不同样式绘制：
    - user → 用户气泡
    - assistant → AI 气泡 + 内嵌工具调用卡片
    - tool → 工具结果
    """
    display_msgs = messages[-max_display:] if len(messages) > max_display else messages

    if not display_msgs:
        uc.draw_empty_state(layout, "在下方输入问题，开始与 AI 对话")
        return

    for msg in display_msgs:
        if msg.role == Role.USER:
            uc.draw_user_message(layout, msg.content, _fmt_time(msg.timestamp))

        elif msg.role == Role.ASSISTANT:
            uc.draw_ai_message(
                layout,
                msg.content,
                _fmt_time(msg.timestamp),
                is_streaming=state.is_processing(),
            )
            # 工具调用卡片
            for tc in msg.tool_calls:
                uc.draw_tool_call_card(
                    layout,
                    tc.tool_name,
                    tc.arguments,
                    status=tc.status.value,
                    result=str(tc.result) if tc.result else "",
                )

        elif msg.role == Role.TOOL:
            # 工具返回结果
            box = uc.draw_info_panel(layout, "工具返回", "Tool output", "tool")
            uc.draw_multiline_text(box, msg.content)

        elif msg.role == Role.SYSTEM:
            # 系统消息用低视觉权重展示
            box = layout.box()
            row = box.row(align=True)
            row.label(text="系统消息", icon=uc.icon("context"))
            row.separator_spacer()
            row.label(text=_fmt_time(msg.timestamp), icon="TIME")
            box.separator(factor=0.2)
            uc.draw_multiline_text(box, msg.content)

        # 消息间距
        layout.separator(factor=0.25)


# ---------------------------------------------------------------------------
# 待确认工具列表
# ---------------------------------------------------------------------------

def draw_pending_tools(layout: bpy.types.UILayout) -> None:
    """绘制待确认工具列表和确认/取消按钮。"""
    pending = state.get_state().pending_tool_calls
    if not pending:
        return

    box = uc.draw_info_panel(layout, "待确认操作", f"{len(pending)} 项待处理", "warn")

    for tc in pending:
        uc.draw_tool_call_card(box, tc.tool_name, tc.arguments, status="pending")

    # 确认/取消按钮
    row = box.row(align=True)
    row.scale_y = 1.1
    row.operator("aiwork.confirm_all_tools", text="确认执行", icon=uc.icon("confirm"))
    row.operator("aiwork.cancel_all_tools", text="全部取消", icon=uc.icon("cancel"))


# ---------------------------------------------------------------------------
# 输入区域
# ---------------------------------------------------------------------------

def draw_input_area(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """绘制底部输入区域：输入框 + 发送/清空按钮。"""
    box = layout.box()
    box.scale_y = 1.0

    header = box.row(align=True)
    header.label(text="快速输入", icon=uc.icon("chat"))
    header.separator_spacer()
    header.label(text="按 Enter 直接发送，Shift+Enter 换行", icon="INFO")

    # 输入框（多行近似——Blender 单行 Text 属性）
    row = box.row(align=True)
    row.scale_y = 1.15
    row.prop(
        context.window_manager,
        INPUT_PROP_NAME,
        text="",
        icon=uc.icon("chat"),
        placeholder="输入你的问题…例如：帮我把选中的立方体旋转 45 度",
    )

    # 按钮行
    btn_row = box.row(align=True)
    is_busy = state.is_processing()

    btn_row.operator(
        "aiwork.chat_send",
        text="发送" if not is_busy else "处理中…",
        icon=uc.icon("send"),
    )
    btn_row.operator(
        "aiwork.chat_clear",
        text="新会话",
        icon=uc.icon("clear"),
    )


# ---------------------------------------------------------------------------
# 主入口：绘制完整聊天面板内容
# ---------------------------------------------------------------------------

def draw_chat_panel(
    layout: bpy.types.UILayout,
    context: bpy.types.Context,
    *,
    show_header: bool = True,
) -> None:
    """绘制聊天面板的全部内容（Tabbed UI）。

    Tab 切换: 对话 | 上下文 | 历史 | 设置
    """
    root = layout.column(align=True)
    root.scale_y = 0.98

    # 获取当前 tab
    try:
        props = context.scene.aiwork_property
    except AttributeError:
        props = None

    # -- 顶部标题栏 --
    if show_header:
        header = root.box()
        top = header.row(align=True)
        top.label(text="AIWork", icon=uc.icon("ai"))
        top.separator_spacer()
        top.label(text="Blender AI 工作台", icon="INFO")

        # 紧凑状态栏
        cs = state.get_state().connection_state
        status_text = {"disconnected": "未连接", "connecting": "连接中",
                       "connected": "已连接", "error": "异常"}.get(cs.value, cs.value)
        status_icon = {"disconnected": uc.icon("cancel"), "connecting": uc.icon("pending"),
                       "connected": uc.icon("done"), "error": uc.icon("error")}.get(cs.value, "DOT")

        stat = header.row(align=True)
        stat.label(text=status_text, icon=status_icon)
        session = state.get_current_session()
        stat.label(text=f"消息 {len(session.messages) if session else 0}", icon=uc.icon("chat"))
        stat.label(text=f"待确认 {len(state.get_state().pending_tool_calls)}", icon=uc.icon("pending"))
        events_count = len(state.get_recent_events())
        if events_count > 0:
            stat.label(text=f"监控 ✓ ({events_count})", icon=uc.icon("done"))

        # Tab 切换栏
        if props:
            tab_row = header.row(align=True)
            tab_row.scale_y = 1.1
            tab_row.prop(props, "active_tab", expand=True)

    # 根据 tab 绘制不同内容
    active_tab = props.active_tab if props else 'CHAT'

    if active_tab == 'CHAT':
        _draw_chat_tab(root, context)
    elif active_tab == 'CONTEXT':
        _draw_context_tab(root, context)
    elif active_tab == 'HISTORY':
        _draw_history_tab(root, context)
    elif active_tab == 'SETTINGS':
        _draw_settings_tab(root, context)


# ---------------------------------------------------------------------------
# Tab: 💬 对话
# ---------------------------------------------------------------------------

def _draw_chat_tab(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """对话 tab：消息流 + 待确认工具 + 输入框。"""
    # 上下文摘要（可折叠）
    session = state.get_current_session()
    if session and session.context_snapshot:
        snap = session.context_snapshot
        ctx_box = layout.box()
        row = ctx_box.row(align=True)
        row.label(text="📐 上下文", icon=uc.icon("context"))
        row.operator("aiwork.refresh_context", text="", icon=uc.icon("refresh"))
        s = snap.scene
        p = snap.project
        ctx_box.label(text=f"场景: {s.scene_name or '(未命名)'} | 选中: {len(s.selected_objects)} 个 | 帧: {s.current_frame}")
        if p.blend_filename:
            ctx_box.label(text=f"文件: {p.blend_filename}")

    # 消息流
    messages = state.get_messages()
    draw_messages(layout, messages)

    # 待确认工具
    draw_pending_tools(layout)

    # 输入区
    draw_input_area(layout, context)


# ---------------------------------------------------------------------------
# Tab: 📊 上下文
# ---------------------------------------------------------------------------

def _draw_context_tab(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """上下文 tab：场景详情 + 项目详情 + 事件监控。"""
    from ..context_builder import collect_context

    layout.operator("aiwork.refresh_context", text="🔄 刷新上下文", icon=uc.icon("refresh"))

    session = state.get_current_session()
    snapshot = session.context_snapshot if session else None

    if snapshot is None:
        uc.draw_empty_state(layout, "点击上方按钮采集上下文")
        return

    s = snapshot.scene
    p = snapshot.project

    # 场景信息
    box = layout.box()
    box.label(text="📐 场景", icon="SCENE_DATA")
    box.label(text=f"名称: {s.scene_name or '(未命名)'}")
    box.label(text=f"对象数: {s.object_count}")
    box.label(text=f"当前帧: {s.current_frame}  [{s.frame_start}-{s.frame_end}]")
    box.label(text=f"渲染引擎: {s.render_engine or '(默认)'}")

    if s.selected_objects:
        sub = box.box()
        sub.label(text=f"✅ 选中对象 ({len(s.selected_objects)})", icon="OBJECT_DATA")
        for obj in s.selected_objects:
            sub.label(text=f"  {obj.name} ({obj.type})")

    # 文件信息
    box = layout.box()
    box.label(text="📁 文件", icon="FILE")
    box.label(text=f"路径: {p.blend_filepath or '(未保存)'}")
    box.label(text=f"状态: {'已保存' if p.is_saved else '未保存'}")
    if p.recent_scripts:
        box.label(text=f"文本块: {', '.join(p.recent_scripts[:5])}")

    # 事件监控
    events = state.get_recent_events(limit=20)
    if events:
        box = layout.box()
        box.label(text=f"📡 最近操作 ({len(events)})", icon="INFO")
        for ev in reversed(events[-10:]):
            box.label(text=f"  {ev}")


# ---------------------------------------------------------------------------
# Tab: 📜 历史
# ---------------------------------------------------------------------------

def _draw_history_tab(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """历史 tab：会话列表（可点击切换）。"""
    from .ui_history import draw_history_panel
    draw_history_panel(layout)


# ---------------------------------------------------------------------------
# Tab: ⚙️ 设置
# ---------------------------------------------------------------------------

def _draw_settings_tab(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """设置 tab：API、MCP、上下文采集参数。"""
    from ..preferences import get_prefs
    prefs = get_prefs(context)

    # API 设置
    box = layout.box()
    box.label(text="🔗 API 连接", icon="URL")
    box.prop(prefs, "api_endpoint", text="端点")
    box.prop(prefs, "api_key", text="API Key")
    box.prop(prefs, "model_name", text="模型")
    row = box.row(align=True)
    row.prop(prefs, "max_tokens")
    row.prop(prefs, "temperature")
    box.prop(prefs, "request_timeout", text="超时 (秒)")

    # MCP 服务器
    box = layout.box()
    box.label(text="🔌 MCP 服务器", icon="NETWORK_DRIVE")
    from ..mcp_server import is_running
    running = is_running()
    box.label(text=f"状态: {'🟢 运行中' if running else '🔴 已停止'}")
    box.prop(prefs, "mcp_enabled", text="启用")
    row = box.row(align=True)
    if running:
        row.operator("aiwork.mcp_stop", text="停止", icon="CANCEL")
    else:
        row.operator("aiwork.mcp_start", text="启动", icon="PLAY")
    row.operator("aiwork.mcp_restart", text="重启", icon="FILE_REFRESH")

    # 上下文采集
    box = layout.box()
    box.label(text="📐 上下文采集", icon="SCENE_DATA")
    box.prop(prefs, "context_max_objects", text="最多对象数")
    row = box.row(align=True)
    row.prop(prefs, "context_include_world", text="世界")
    row.prop(prefs, "context_include_render", text="渲染")
    box.prop(prefs, "context_refresh_interval", text="自动刷新 (秒)")

    # 会话管理
    box = layout.box()
    box.label(text="💬 会话", icon="FILE_TEXT")
    row = box.row(align=True)
    row.operator("aiwork.chat_new_session", text="新建", icon="ADD")
    row.operator("aiwork.chat_clear", text="清空", icon="TRASH")

    # -- 上下文摘要 --
    session = state.get_current_session()
    if session and session.context_snapshot:
        ctx = session.context_snapshot
        ctx_box = uc.draw_info_panel(root, "当前上下文", ctx.project.blend_filename or "未保存文件", "context")
        ctx_row = ctx_box.row(align=True)

        # 摘要信息
        s = ctx.scene
        p = ctx.project
        uc.draw_status_chip(ctx_box, "场景", s.scene_name or "(未命名)", "scene")
        if p.blend_filename:
            uc.draw_status_chip(ctx_box, "文件", p.blend_filename, "file")
        uc.draw_status_chip(ctx_box, "选中", f"{len(s.selected_objects)} 个对象", "context")
        if s.current_frame:
            uc.draw_status_chip(ctx_box, "帧", str(s.current_frame), "pending")

    # -- 消息列表 --
    messages = state.get_messages()
    stream_box = uc.draw_info_panel(root, "对话记录", f"最近 {min(len(messages), 50)} 条", "chat")
    draw_messages(stream_box, messages)

    # -- 待确认工具 --
    draw_pending_tools(root)

    # -- 输入区 --
    draw_input_area(root, context)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _fmt_time(timestamp: float) -> str:
    """把 Unix 时间戳格式化为 HH:MM:SS。"""
    import time
    return time.strftime("%H:%M:%S", time.localtime(timestamp))
