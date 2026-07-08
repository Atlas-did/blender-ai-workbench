"""
context_project.py — 工程信息采集
==================================
采集当前 Blend 文件的工程级信息：
- 文件路径、文件名、保存状态
- 最近脚本目录
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import bpy

from .schemas import ProjectContext

log = logging.getLogger(__name__)


def collect_project_context(
    context: Optional[bpy.types.Context] = None,
) -> ProjectContext:
    """采集当前工程上下文。

    Args:
        context: Blender 上下文，默认使用 bpy.context。

    Returns:
        ProjectContext: 工程上下文。
    """
    if context is None:
        context = bpy.context

    ctx = ProjectContext()

    blend = bpy.data
    filepath = bpy.data.filepath

    if filepath:
        ctx.blend_filepath = filepath
        ctx.blend_filename = os.path.basename(filepath)
        ctx.is_saved = True
    else:
        ctx.blend_filename = "未保存"
        ctx.is_saved = False

    # -- 最近脚本（Text Editor 中的文本块） --
    texts = bpy.data.texts
    ctx.recent_scripts = [t.name for t in texts[:20]]

    log.debug(
        "工程上下文采集完成: file=%s saved=%s scripts=%d",
        ctx.blend_filename, ctx.is_saved, len(ctx.recent_scripts),
    )
    return ctx
