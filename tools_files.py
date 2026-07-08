"""
tools_files.py — 文件系统操作工具
==================================
允许 AI 读取工程目录下的文件，受路径沙箱限制。

风险说明：
- 读文件 / 列目录: MEDIUM（限定在工作目录内）
- 写文件: HIGH（需要用户确认 + 限定在工程目录内）
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# 读写大小限制
MAX_READ_SIZE = 50000   # 字符
MAX_LIST_ENTRIES = 200


def _workspace_root() -> str:
    """获取工作区根目录（当前 blend 文件所在目录，或用户文档目录）。"""
    import bpy
    fp = bpy.data.filepath
    if fp:
        return os.path.dirname(os.path.abspath(fp))
    # 未保存的 blend 文件 → 使用用户文档目录
    return os.path.expanduser("~")


def _is_safe_path(path: str) -> bool:
    """检查路径是否在工作区内（防止路径遍历攻击）。"""
    root = os.path.abspath(_workspace_root())
    try:
        full = os.path.abspath(os.path.join(root, path))
    except (ValueError, OSError):
        return False

    # 规范化后必须在 root 内
    full_norm = os.path.normpath(full)
    root_norm = os.path.normpath(root)

    # 必须在 root 之内，且不能有 .. 遍历
    if os.path.commonpath([full_norm, root_norm]) != root_norm:
        # 如果路径在文件系统根目录之外（如 Windows 驱动器）
        return False

    return True


def _safe_full_path(path: str) -> str | None:
    """将相对路径转为工作区内的绝对路径，不安全则返回 None。"""
    root = _workspace_root()
    # 支持绝对路径（但仍然限制在工作区内）
    if os.path.isabs(path):
        full = os.path.abspath(path)
    else:
        full = os.path.abspath(os.path.join(root, path))

    if not _is_safe_path(full):
        return None
    return full


def list_directory(directory: str = ".") -> dict:
    """列出目录内容（仅限工作区范围内）。

    Args:
        directory: 目录路径（相对于 blend 文件目录）。

    Returns:
        {"directory": str, "files": [...], "directories": [...]} 或 {"error": str}
    """
    full = _safe_full_path(directory)
    if full is None:
        return {"error": f"目录不在工作区内: {directory}"}

    if not os.path.isdir(full):
        return {"error": f"路径不是目录: {directory}"}

    try:
        entries = os.listdir(full)
    except PermissionError:
        return {"error": f"没有权限读取目录: {directory}"}
    except Exception as exc:
        return {"error": f"读取目录失败: {exc}"}

    # 排序：目录优先，然后文件
    entries.sort(key=lambda e: (not os.path.isdir(os.path.join(full, e)), e.lower()))

    files = []
    dirs = []
    for e in entries[:MAX_LIST_ENTRIES]:
        target = os.path.join(full, e)
        try:
            if os.path.isfile(target):
                size = os.path.getsize(target)
                files.append({"name": e, "size": size})
            elif os.path.isdir(target):
                dirs.append({"name": e})
        except OSError:
            pass  # 跳过无法访问的条目

    truncated = len(entries) > MAX_LIST_ENTRIES
    result = {
        "directory": directory,
        "files": files,
        "directories": dirs,
    }
    if truncated:
        result["truncated"] = f"仅显示前 {MAX_LIST_ENTRIES} 项，共 {len(entries)} 项"

    log.info("列出目录: %s → %d 文件, %d 目录", directory, len(files), len(dirs))
    return result


def read_file(filepath: str, max_chars: int = MAX_READ_SIZE) -> dict:
    """读取文本文件内容（仅限工作区范围内）。

    Args:
        filepath: 文件路径（相对于 blend 文件目录）。

    Returns:
        {"filepath": str, "content": str, "size": int, "truncated": bool} 或 {"error": str}
    """
    full = _safe_full_path(filepath)
    if full is None:
        return {"error": f"文件不在工作区内: {filepath}"}

    if not os.path.isfile(full):
        return {"error": f"文件不存在: {filepath}"}

    try:
        file_size = os.path.getsize(full)
    except OSError:
        file_size = 0

    # 拒绝过大的文件
    if file_size > 10 * 1024 * 1024:  # 10MB
        return {"error": f"文件过大: {filepath} ({file_size / 1024 / 1024:.1f} MB)"}

    try:
        # 尝试 UTF-8，失败则用 latin-1
        content = None
        for encoding in ("utf-8", "latin-1"):
            try:
                with open(full, "r", encoding=encoding) as f:
                    content = f.read(max_chars + 1)  # 多读 1 个字符检测截断
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return {"error": f"无法解码文件: {filepath}（不是文本文件？）"}

    except PermissionError:
        return {"error": f"没有权限读取文件: {filepath}"}
    except Exception as exc:
        return {"error": f"读取文件失败: {exc}"}

    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]

    log.info("读取文件: %s → %d 字符 (截断=%s)", filepath, len(content), truncated)
    return {
        "filepath": filepath,
        "size": file_size,
        "content": content,
        "truncated": truncated,
    }


def write_file(filepath: str, content: str) -> dict:
    """写入文本文件（仅限工作区范围内，风险等级 HIGH）。

    Args:
        filepath: 文件路径（相对于 blend 文件目录）。
        content: 要写入的文本内容。

    Returns:
        {"filepath": str, "bytes_written": int} 或 {"error": str}
    """
    full = _safe_full_path(filepath)
    if full is None:
        return {"error": f"文件不在工作区内: {filepath}"}

    # 不允许覆盖 .blend 文件
    if full.lower().endswith(".blend"):
        return {"error": "不允许覆盖 .blend 文件"}

    # 如果目标已存在，备份
    backup = None
    if os.path.exists(full):
        try:
            with open(full, "r", encoding="utf-8") as f:
                backup = f.read(100000)
        except Exception:
            pass

    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        size = len(content.encode("utf-8"))
        log.info("写入文件: %s → %d 字节", filepath, size)
        return {"filepath": filepath, "bytes_written": size}
    except PermissionError:
        return {"error": f"没有权限写入文件: {filepath}"}
    except Exception as exc:
        return {"error": f"写入文件失败: {exc}"}
