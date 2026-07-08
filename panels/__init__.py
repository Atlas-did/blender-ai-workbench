"""panels/ — Blender Panel 注册。"""

from __future__ import annotations

import bpy

from .panel_chat import AIWORK_PT_Chat, AIWORK_PT_ChatContext, AIWORK_PT_ChatLogs

CLASSES = [
    AIWORK_PT_Chat,
    AIWORK_PT_ChatContext,
    AIWORK_PT_ChatLogs,
]

register_class, unregister_class = bpy.utils.register_classes_factory(CLASSES)


def register():
    register_class()


def unregister():
    unregister_class()
