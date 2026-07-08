"""aiwork 单文件入口。

这个文件是 Blender 实际启用的入口，负责把同目录下的 aiwork 包
以标准包方式加载出来，然后把 register / unregister 透传给 Blender。

使用方式：
1. 保留当前目录下的 __init__.py 和各个子模块文件
2. 在 Blender 里安装/启用这个 addon.py
3. Blender 会通过这里进入真正的 aiwork 包
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

bl_info = {
    "name": "AIWork",
    "author": "finef",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "View3D > Sidebar > AIWork",
    "description": "AI 原生 Blender 工作台",
    "category": "Interface",
}

_ROOT = pathlib.Path(__file__).resolve().parent
_PKG_NAME = "_aiwork_pkg"
_PKG_INIT = _ROOT / "__init__.py"


def _load_package() -> ModuleType:
    existing = sys.modules.get(_PKG_NAME)
    if existing is not None:
        existing_file = getattr(existing, "__file__", "")
        if existing_file and pathlib.Path(existing_file).resolve() == _PKG_INIT:
            return existing

    # 清理同名残留，避免 Blender 先把入口文件自身占到模块名上。
    sys.modules.pop(_PKG_NAME, None)

    spec = importlib.util.spec_from_file_location(
        _PKG_NAME,
        _PKG_INIT,
        submodule_search_locations=[str(_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 aiwork 包入口: {_PKG_INIT}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_PKG_NAME] = module
    spec.loader.exec_module(module)
    return module


_pkg = _load_package()

register = _pkg.register
unregister = _pkg.unregister
