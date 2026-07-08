"""
tools_python.py — Python 脚本执行工具
======================================
允许 AI 运行受控的 Python 代码片段，在受限沙箱中执行。

注意：此工具风险等级为 HIGH，需要用户输入 YES 确认。
"""

from __future__ import annotations

import io
import logging
import sys
import threading

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 安全：禁止的 builtins 和模块
# ---------------------------------------------------------------------------

_DISALLOWED_BUILTINS = {
    "open", "compile", "eval", "exec", "execfile", "input",
    "__import__", "breakpoint", "memoryview",
}

_DISALLOWED_MODULES = {
    "os", "subprocess", "shutil", "sys", "importlib",
    "ctypes", "signal", "socket", "http", "urllib",
    "ftplib", "telnetlib", "smtplib", "poplib", "imaplib",
    "pathlib", "glob", "fnmatch", "tempfile", "zipfile",
    "tarfile", "gzip", "bz2", "lzma",
    "multiprocessing", "threading", "concurrent",
    "pickle", "shelve", "marshal",
    "builtins", "__builtins__",
}


def run_python_snippet(code: str, timeout: int = 10) -> dict:
    """在受限沙箱中执行 Python 代码片段。

    Args:
        code: Python 代码字符串。
        timeout: 最长执行时间（秒）。

    Returns:
        {"output": str, "error": str}
    """
    # 捕获 stdout/stderr
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    result = {"output": "", "error": ""}

    def _execute() -> None:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_buf
        sys.stderr = stderr_buf

        try:
            # 构建受限的全局命名空间
            safe_globals = _build_safe_globals()

            # 编译代码（检查语法）
            try:
                compiled = compile(code, "<aiwork_sandbox>", "exec")
            except SyntaxError as e:
                result["error"] = f"语法错误: {e}"
                return

            # 执行
            exec(compiled, safe_globals)

        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    # 在独立线程中执行，支持超时
    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        result["error"] = f"代码执行超时 ({timeout}s)"

    result["output"] = stdout_buf.getvalue()
    err_output = stderr_buf.getvalue()
    if err_output:
        result["output"] += "\n[stderr]\n" + err_output

    # 截断过长输出
    max_len = 5000
    if len(result["output"]) > max_len:
        result["output"] = result["output"][:max_len] + "\n…(输出已截断)"

    log.info("Python 沙箱执行完成: output=%d chars, error=%s",
             len(result["output"]), result["error"][:80] if result["error"] else "无")
    return result


def _build_safe_globals() -> dict:
    """构建受限的全局命名空间。

    包含安全的 builtins 以及 Blender bpy / bmesh 模块。
    """
    import builtins as _builtins

    safe_builtins = {}
    for name in dir(_builtins):
        if name.startswith("_"):
            continue
        if name in _DISALLOWED_BUILTINS:
            continue
        obj = getattr(_builtins, name)
        if callable(obj) or isinstance(obj, type):
            safe_builtins[name] = obj

    safe_globals = {
        "__builtins__": safe_builtins,
        "__name__": "__aiwork_sandbox__",
    }

    # 安全注入 Blender 模块
    _safe_import(safe_globals, "bpy", "bpy")
    _safe_import(safe_globals, "bmesh", "bmesh")
    _safe_import(safe_globals, "math", "math")
    _safe_import(safe_globals, "mathutils", "mathutils")
    _safe_import(safe_globals, "random", "random")
    _safe_import(safe_globals, "json", "json")
    _safe_import(safe_globals, "re", "re")
    _safe_import(safe_globals, "collections", "collections")
    _safe_import(safe_globals, "itertools", "itertools")
    _safe_import(safe_globals, "functools", "functools")

    return safe_globals


def _safe_import(safe_globals: dict, name: str, module_name: str) -> None:
    """安全导入模块并注入到 safe_globals 中。"""
    try:
        import importlib
        mod = importlib.import_module(module_name)
        safe_globals[name] = mod
    except Exception:
        pass  # 模块不可用时跳过
