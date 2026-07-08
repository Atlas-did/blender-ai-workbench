"""
context_scene.py — 场景信息采集
================================
采集当前 Blender 场景的状态：
- 场景名、对象统计
- 选中对象列表（名称、类型、位置、可见性、选中态）
- 帧范围、当前帧
- 渲染引擎
- 世界/环境信息（可选）
"""

from __future__ import annotations

import logging
from typing import Optional

import bpy

from .schemas import SceneContext, SceneObjectInfo
from .settings import DEFAULT_CONTEXT_MAX_OBJECTS

log = logging.getLogger(__name__)


def collect_scene_context(
    context: Optional[bpy.types.Context] = None,
    max_objects: int = DEFAULT_CONTEXT_MAX_OBJECTS,
    include_world: bool = True,
    include_render: bool = True,
) -> SceneContext:
    """采集当前场景上下文。

    Args:
        context: Blender 上下文，默认使用 bpy.context。
        max_objects: 最多上报的对象数量（防止上下文过大）。
        include_world: 是否包含世界/环境信息。
        include_render: 是否包含渲染设置。

    Returns:
        SceneContext: 场景上下文快照。
    """
    if context is None:
        context = bpy.context

    scene = context.scene
    if scene is None:
        log.warning("无法获取当前场景")
        return SceneContext()

    ctx = SceneContext()
    ctx.scene_name = scene.name

    # -- 对象统计 --
    all_objects = list(scene.objects)
    ctx.object_count = len(all_objects)

    # -- 选中对象 --
    selected = context.selected_objects
    ctx.selected_objects = [
        _obj_to_info(obj, selected=True)
        for obj in selected[:max_objects]
    ]

    # -- 可见对象（排除选中，避免重复） --
    selected_names = {o.name for o in selected}
    visible = [
        obj for obj in all_objects
        if obj.visible_get() and obj.name not in selected_names
    ]
    remaining = max(0, max_objects - len(ctx.selected_objects))
    ctx.visible_objects = [
        _obj_to_info(obj, selected=False)
        for obj in visible[:remaining]
    ]

    # -- 帧 --
    ctx.current_frame = scene.frame_current
    ctx.frame_start = scene.frame_start
    ctx.frame_end = scene.frame_end

    # -- 渲染 --
    if include_render:
        ctx.render_engine = scene.render.engine

    # -- 世界 --
    if include_world and scene.world:
        ctx.world_name = scene.world.name

    log.debug(
        "场景上下文采集完成: scene=%s objects=%d selected=%d",
        ctx.scene_name, ctx.object_count, len(ctx.selected_objects),
    )
    return ctx


def collect_selection_summary(
    context: Optional[bpy.types.Context] = None,
) -> dict:
    """快速收集选中对象的摘要信息（用于简短上下文注入）。"""
    if context is None:
        context = bpy.context

    selected = context.selected_objects
    if not selected:
        return {"count": 0, "objects": []}

    summary = []
    for obj in selected:
        loc = obj.location
        summary.append({
            "name": obj.name,
            "type": obj.type,
            "location": (round(loc.x, 3), round(loc.y, 3), round(loc.z, 3)),
            "visible": obj.visible_get(),
        })

    return {"count": len(selected), "objects": summary}


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _obj_to_info(obj: bpy.types.Object, selected: bool = False) -> SceneObjectInfo:
    """把 Blender Object 转成 SceneObjectInfo。"""
    loc = obj.location
    return SceneObjectInfo(
        name=obj.name,
        type=obj.type,
        location=(round(loc.x, 4), round(loc.y, 4), round(loc.z, 4)),
        visible=obj.visible_get(),
        selected=selected,
        children_count=len(obj.children),
    )
