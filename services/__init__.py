"""services/ — 后台服务和事件系统。"""

from __future__ import annotations

import bpy

modules = [
    "service_bridge",
    "service_worker",
    "service_events",
    "service_stream",
]

reg, unreg = bpy.utils.register_submodule_factory(__package__, modules)


def register():
    reg()


def unregister():
    unreg()
