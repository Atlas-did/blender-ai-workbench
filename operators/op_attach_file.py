"""
op_attach_file.py — 附件上传 Operator
======================================
让用户选择图片或文本文件，发送给 AI 进行分析。

图片: 转 base64 → Vision API 格式
文本: 读取内容 → 附加到消息中
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os

import bpy
from bpy.props import StringProperty, CollectionProperty
from bpy.types import Operator

from .. import state

log = logging.getLogger(__name__)

# 支持的文件类型
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.tif'}
TEXT_EXTS = {'.py', '.txt', '.md', '.json', '.xml', '.csv', '.yaml', '.yml',
             '.obj', '.mtl', '.gltf', '.glb', '.fbx', '.stl', '.ply', '.usd',
             '.hdr', '.exr'}


def _get_mime_type(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    mime_map = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff', '.tif': 'image/tiff',
    }
    return mime_map.get(ext, 'application/octet-stream')


def _is_image(filepath: str) -> bool:
    return os.path.splitext(filepath)[1].lower() in IMAGE_EXTS


def _read_as_base64(filepath: str) -> str:
    """读取文件为 base64 字符串。"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def _read_as_text(filepath: str, max_chars: int = 10000) -> str:
    """读取文本文件内容。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read(max_chars + 1)
        if len(content) > max_chars:
            content = content[:max_chars] + "\n…(文件过长，已截断)"
        return content
    except UnicodeDecodeError:
        return "[二进制文件，无法以文本方式读取]"


def attach_file(filepath: str) -> dict | None:
    """读取文件并存入附件列表。

    Returns:
        附件信息 dict，失败返回 None。
    """
    if not os.path.isfile(filepath):
        log.error("文件不存在: %s", filepath)
        return None

    filename = os.path.basename(filepath)
    is_img = _is_image(filepath)

    attachment = {
        "filepath": filepath,
        "filename": filename,
        "is_image": is_img,
        "mime_type": _get_mime_type(filepath),
    }

    if is_img:
        # 限制图片大小 (10MB)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if size_mb > 10:
            log.warning("图片过大 (%.1f MB)，跳过: %s", size_mb, filepath)
            return None
        attachment["base64"] = _read_as_base64(filepath)
    else:
        attachment["content"] = _read_as_text(filepath)

    state.add_attachment(attachment)
    log.info("已附加: %s (%s)", filename, "图片" if is_img else "文本")
    return attachment


def clear_attachments() -> None:
    state.clear_attachments()


def get_attachments() -> list[dict]:
    return state.get_state().attachments


# ---------------------------------------------------------------------------
# Operator
# ---------------------------------------------------------------------------

class AIWORK_OT_AttachFile(Operator):
    """选择文件发送给 AI"""
    bl_idname = "aiwork.attach_file"
    bl_label = "附加文件"
    bl_description = "选择图片或文本文件附加到对话中"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(subtype='FILE_PATH')  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        if not self.filepath:
            return {'CANCELLED'}

        result = attach_file(self.filepath)
        if result is None:
            self.report({'ERROR'}, f"无法附加: {os.path.basename(self.filepath)}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"已附加: {result['filename']}")
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class AIWORK_OT_RemoveAttachment(Operator):
    """移除附件"""
    bl_idname = "aiwork.remove_attachment"
    bl_label = "移除附件"
    bl_description = "移除该附件"
    bl_options = {'REGISTER', 'UNDO'}

    index: bpy.props.IntProperty(name="索引", default=-1)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        atts = state.get_state().attachments
        if 0 <= self.index < len(atts):
            removed = atts.pop(self.index)
            self.report({'INFO'}, f"已移除: {removed['filename']}")
        return {'FINISHED'}


class AIWORK_OT_ClearAttachments(Operator):
    """清空所有附件"""
    bl_idname = "aiwork.clear_attachments"
    bl_label = "清空附件"
    bl_description = "移除所有已附加的文件"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        count = len(state.get_state().attachments)
        state.get_state().attachments.clear()
        self.report({'INFO'}, f"已清空 {count} 个附件")
        return {'FINISHED'}
