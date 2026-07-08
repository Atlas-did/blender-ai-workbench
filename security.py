"""
security.py — 安全策略与风险分级
=================================
定义工具执行的安全策略：
- 风险分级（low / medium / high）
- 确认规则（哪些操作必须用户确认）
- 沙箱边界（文件读写范围、Python 执行限制）
"""

from __future__ import annotations

import os

from .schemas import RiskLevel


def requires_confirmation(risk: RiskLevel) -> bool:
    """判断给定风险等级是否需要用户确认。

    - LOW: 纯读取操作，无需确认
    - MEDIUM: 修改场景数据，需要确认（可批量）
    - HIGH: 执行代码 / 文件写入，必须逐个确认
    """
    return risk in (RiskLevel.MEDIUM, RiskLevel.HIGH)


def requires_text_confirmation(risk: RiskLevel) -> bool:
    """高风险操作是否需要用户输入特定文本确认。"""
    return risk == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# 路径沙箱
# ---------------------------------------------------------------------------

def workspace_root() -> str:
    """获取工作区根目录。"""
    import bpy
    fp = bpy.data.filepath
    if fp:
        return os.path.dirname(os.path.abspath(fp))
    return os.path.expanduser("~")


def is_safe_file_path(path: str, workspace_root_param: str | None = None) -> bool:
    """检查文件路径是否在安全范围内（防止路径遍历攻击）。"""
    if workspace_root_param is None:
        workspace_root_param = workspace_root()

    root = os.path.abspath(workspace_root_param)

    try:
        full = os.path.abspath(path)
    except (ValueError, OSError):
        return False

    root_norm = os.path.normpath(root)
    full_norm = os.path.normpath(full)

    # 检查是否在 root 内
    try:
        common = os.path.commonpath([full_norm, root_norm])
    except ValueError:
        return False

    if common != root_norm:
        return False

    # 检查没有 .. 穿越
    if ".." in os.path.relpath(full_norm, root_norm).split(os.sep):
        return False

    return True


def resolve_safe_path(rel_path: str, workspace_root_param: str | None = None) -> str | None:
    """将相对路径解析为工作区内的安全绝对路径。

    Returns:
        安全的绝对路径，或 None（路径不安全）。
    """
    if workspace_root_param is None:
        workspace_root_param = workspace_root()

    root = os.path.abspath(workspace_root_param)

    if os.path.isabs(rel_path):
        full = os.path.abspath(rel_path)
    else:
        full = os.path.abspath(os.path.join(root, rel_path))

    if is_safe_file_path(full, workspace_root_param):
        return full
    return None


# ---------------------------------------------------------------------------
# Python 代码安全检查
# ---------------------------------------------------------------------------

FORBIDDEN_PATTERNS = [
    "os.system", "os.popen", "os.exec",
    "subprocess",
    "shutil.rmtree", "shutil.copy",
    "__import__('os')", '__import__("os")',
    "eval(", "exec(",
    "open(",
    "importlib",
    "ctypes",
    "socket",
    "urllib",
    "requests",
]


def scan_code_for_danger(code: str) -> list[str]:
    """扫描 Python 代码中的危险模式。

    Returns:
        检测到的危险模式列表（空列表表示安全）。
    """
    found = []
    code_lower = code.lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in code_lower:
            found.append(pattern)
    return found
