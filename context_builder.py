"""
context_builder.py — 上下文聚合器
==================================
把场景、工程、选择集等信息拼装为完整的 ContextSnapshot，
序列化为 AI 可读的文本注入 prompt。
"""

from __future__ import annotations

import logging
from typing import Optional

import bpy

from .context_project import collect_project_context
from .context_scene import collect_scene_context
from .preferences import get_prefs
from .schemas import ContextSnapshot

log = logging.getLogger(__name__)


def collect_context(
    context: Optional[bpy.types.Context] = None,
) -> ContextSnapshot:
    """一站式采集完整上下文。

    从偏好设置中读取采集选项，控制采集范围和粒度。

    Args:
        context: Blender 上下文。

    Returns:
        ContextSnapshot: 完整的上下文快照。
    """
    prefs = get_prefs(context)

    scene_ctx = collect_scene_context(
        context=context,
        max_objects=prefs.context_max_objects,
        include_world=prefs.context_include_world,
        include_render=prefs.context_include_render,
    )

    project_ctx = collect_project_context(context=context)

    snapshot = ContextSnapshot(
        scene=scene_ctx,
        project=project_ctx,
    )

    log.info("上下文采集完成: %s", snapshot.to_text()[:120])
    return snapshot


def build_system_prompt(snapshot: ContextSnapshot) -> str:
    """基于上下文快照构建 system prompt 注入文本。

    Returns:
        str: 可直接注入到 messages[0] 的 system prompt 文本。
    """
    parts = [
        "你是一个 Blender 3D 助手，运行在 Blender 内部插件中。",
        "你可以帮助用户进行 3D 建模、场景管理、渲染设置等操作。",
        "",
        snapshot.to_text(),
        "",
        "当用户要求执行操作时，先解释你的计划，再调用相应的工具。",
        "对于修改场景的操作，务必先告知用户将要做什么。",
    ]
    return "\n".join(parts)
