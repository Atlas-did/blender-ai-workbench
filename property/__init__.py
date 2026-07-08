"""
property.py — Blender PropertyGroup 定义
=========================================
参考 BlenderAIStudio 的 SceneProperty 模式，
将 AIWork 的核心状态挂载到 bpy.types.Scene 上，
随 .blend 文件持久化，不再依赖 JSON 文件存储。

挂载点:
    bpy.types.Scene.aiwork_property → AIWorkSceneProperty
"""

from __future__ import annotations

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

# ---------------------------------------------------------------------------
# 提供者枚举（动态生成 + 缓存）
# ---------------------------------------------------------------------------

_provider_enum_items: list[tuple[str, str, str]] = []


def _refresh_provider_enum() -> None:
    global _provider_enum_items
    _provider_enum_items.clear()
    from ..providers.registry import list_provider_ids
    for pid in list_provider_ids():
        _provider_enum_items.append((pid, pid, ""))


def _provider_items(self, context):
    if not _provider_enum_items:
        _refresh_provider_enum()
    return _provider_enum_items


# ---------------------------------------------------------------------------
# 模型枚举
# ---------------------------------------------------------------------------

def _model_items(self, context):
    """根据当前选中的 provider 动态返回模型列表。"""
    provider_id = self.api_provider
    if not provider_id:
        return [("", "请先选择 Provider", "")]
    try:
        from ..providers.registry import get_provider
        provider = get_provider(provider_id)
        models = provider.list_models()
        return [(m, m, "") for m in models]
    except Exception:
        return [("", "无法获取模型列表", "")]


# ---------------------------------------------------------------------------
# 会话消息 Item（CollectionProperty 子项）
# ---------------------------------------------------------------------------

class AIWorkMessageItem(bpy.types.PropertyGroup):
    """聊天消息的 Blender PropertyGroup。"""
    role: StringProperty(name="角色")  # user / assistant / system / tool
    content: StringProperty(name="内容", maxlen=65536)
    tool_calls_json: StringProperty(name="工具调用 JSON", maxlen=65536)
    timestamp: FloatProperty(name="时间戳")


# ---------------------------------------------------------------------------
# 会话 Item
# ---------------------------------------------------------------------------

class AIWorkSessionItem(bpy.types.PropertyGroup):
    """对话会话的 Blender PropertyGroup。"""
    session_id: StringProperty(name="会话 ID")
    title: StringProperty(name="标题", default="新会话")
    created_at: FloatProperty(name="创建时间")
    updated_at: FloatProperty(name="更新时间")
    messages_json: StringProperty(name="消息 JSON", maxlen=1048576)


# ---------------------------------------------------------------------------
# 场景属性（主 PropertyGroup）
# ---------------------------------------------------------------------------

class AIWorkSceneProperty(bpy.types.PropertyGroup):
    """挂载在 bpy.types.Scene 上的 AIWork 主属性组。"""

    # -- 聊天输入 --
    chat_input: StringProperty(
        name="聊天输入",
        description="输入你的问题",
        maxlen=4000,
        options={'SKIP_SAVE'},
    )

    # -- API / Provider --
    api_provider: EnumProperty(
        name="API Provider",
        description="选择 AI 服务提供商",
        items=_provider_items,
    )

    api_endpoint: StringProperty(
        name="API 端点",
        description="LLM API 端点 URL（OpenAI 兼容格式）",
        default="https://api.moonshot.cn/v1",
    )

    api_key: StringProperty(
        name="API Key",
        description="API 密钥",
        subtype='PASSWORD',
    )

    model_name: EnumProperty(
        name="模型",
        description="选择 LLM 模型",
        items=_model_items,
    )

    # -- 生成参数 --
    max_tokens: IntProperty(
        name="最大 Token 数",
        default=4096, min=64, max=65536, soft_max=16384,
    )

    temperature: FloatProperty(
        name="Temperature",
        default=1.0, min=0.0, max=2.0, step=0.05,
    )

    request_timeout: IntProperty(
        name="请求超时 (秒)",
        default=120, min=5, max=300,
    )

    # -- MCP 服务器 --
    mcp_enabled: BoolProperty(name="启用 MCP 服务器", default=False)
    mcp_port: IntProperty(name="MCP 端口", default=9876, min=1024, max=65535)
    mcp_auto_start: BoolProperty(name="自动启动 MCP", default=False)

    # -- 上下文采集 --
    context_max_objects: IntProperty(name="最多对象数", default=50, min=5, max=500)
    context_include_world: BoolProperty(name="采集世界", default=True)
    context_include_render: BoolProperty(name="采集渲染", default=True)
    context_refresh_interval: FloatProperty(
        name="自动刷新 (秒)", default=2.0, min=0.0, max=30.0, step=0.5,
    )

    # -- 会话管理 --
    active_session_index: IntProperty(name="当前会话索引", default=-1)
    sessions_json: StringProperty(
        name="会话列表 JSON",
        description="所有会话的 JSON 序列化",
        maxlen=10485760,  # 10MB
    )

    # -- UI 状态 --
    expand_chat: BoolProperty(name="展开聊天面板", default=True)
    expand_context: BoolProperty(name="展开上下文面板", default=True)
    expand_settings: BoolProperty(name="展开设置面板", default=False)
    expand_mcp: BoolProperty(name="展开 MCP 面板", default=False)
    expand_events: BoolProperty(name="展开事件监控", default=False)

    # -- 开发者 --
    use_dev_ui: BoolProperty(name="开发者 UI", default=False)

    # -- Tab 切换 --
    active_tab: EnumProperty(
        name="标签",
        items=[
            ('CHAT', "对话", "AI 对话界面"),
            ('CONTEXT', "上下文", "场景详情与事件监控"),
            ('HISTORY', "历史", "会话历史"),
            ('SETTINGS', "设置", "API、MCP、采集参数"),
        ],
        default='CHAT',
    )

    # -- 最近事件（只读展示） --
    recent_events_text: StringProperty(
        name="最近事件",
        description="Blender 操作监控摘要",
        maxlen=4096,
    )


# ---------------------------------------------------------------------------
# 注册 / 注销
# ---------------------------------------------------------------------------

CLASSES = [
    AIWorkMessageItem,
    AIWorkSessionItem,
    AIWorkSceneProperty,
]

register_class, unregister_class = bpy.utils.register_classes_factory(CLASSES)


def register():
    register_class()
    bpy.types.Scene.aiwork_property = PointerProperty(type=AIWorkSceneProperty)
    # 迁移旧的 WindowManager 属性
    if hasattr(bpy.types.WindowManager, "aiwork_chat_input"):
        # 保留兼容但不新建
        pass
    else:
        bpy.types.WindowManager.aiwork_chat_input = StringProperty(
            name="aiwork_chat_input",
            default="",
            maxlen=4000,
            options={'SKIP_SAVE'},
        )


def unregister():
    del bpy.types.Scene.aiwork_property
    if hasattr(bpy.types.WindowManager, "aiwork_chat_input"):
        del bpy.types.WindowManager.aiwork_chat_input
    unregister_class()
