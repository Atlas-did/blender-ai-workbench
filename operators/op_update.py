"""
op_update.py — 一键更新 + 重载插件
===================================
从 GitHub 拉取最新代码，然后自动重载插件。
要求插件目录是一个 git 仓库（通过 git clone 安装）。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

import bpy
from bpy.types import Operator

log = logging.getLogger(__name__)


class AIWORK_OT_CheckUpdate(Operator):
    """检查更新：git pull 拉取最新代码并重载插件"""
    bl_idname = "aiwork.check_update"
    bl_label = "检查更新"
    bl_description = "从 GitHub 拉取最新版本并重载插件"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        addon_dir = _addon_dir()
        if addon_dir is None:
            self.report({'ERROR'}, "无法确定插件目录")
            return {'CANCELLED'}

        if not os.path.isdir(os.path.join(addon_dir, ".git")):
            self.report({'ERROR'}, "插件目录不是 git 仓库，无法自动更新。请通过 git clone 重新安装。")
            return {'CANCELLED'}

        # 1. git fetch + git pull
        try:
            result = subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=addon_dir,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            self.report({'ERROR'}, "未找到 git 命令，请安装 Git for Windows")
            return {'CANCELLED'}
        except subprocess.TimeoutExpired:
            self.report({'ERROR'}, "git pull 超时")
            return {'CANCELLED'}
        except Exception as exc:
            self.report({'ERROR'}, f"git pull 失败: {exc}")
            return {'CANCELLED'}

        output = (result.stdout + result.stderr).strip()

        if "Already up to date" in output or "Already up-to-date" in output:
            self.report({'INFO'}, "已是最新版本")
            return {'FINISHED'}

        if result.returncode != 0:
            self.report({'ERROR'}, f"git pull 失败:\n{output[:300]}")
            return {'CANCELLED'}

        # 2. 有更新！重载插件
        log.info("检测到更新，正在重载插件…\ngit output:\n%s", output)

        # 清除已缓存的模块，确保重载时加载最新代码
        _purge_cached_modules()

        # 3. 禁用 → 启用（等效重载）
        try:
            bpy.ops.preferences.addon_disable(module=__package__)
        except Exception:
            pass  # 可能已经禁用

        try:
            bpy.ops.preferences.addon_enable(module=__package__)
        except Exception as exc:
            self.report({'ERROR'}, f"重载失败: {exc}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"已更新并重载！\n{output[:200]}")
        return {'FINISHED'}


class AIWORK_OT_GitLog(Operator):
    """查看最近更新日志"""
    bl_idname = "aiwork.git_log"
    bl_label = "更新日志"
    bl_description = "查看最近 5 条提交记录"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context) -> set[str]:
        addon_dir = _addon_dir()
        if addon_dir is None:
            self.report({'ERROR'}, "无法确定插件目录")
            return {'CANCELLED'}

        if not os.path.isdir(os.path.join(addon_dir, ".git")):
            self.report({'ERROR'}, "插件目录不是 git 仓库")
            return {'CANCELLED'}

        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                cwd=addon_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            log_text = result.stdout.strip() or "(无提交记录)"
        except Exception as exc:
            log_text = f"获取日志失败: {exc}"

        # 弹出对话框展示日志
        def _draw(self, _context):
            for line in log_text.split("\n"):
                self.layout.label(text=line)

        bpy.context.window_manager.popup_menu(_draw, title="AIWork 更新日志", icon='TEXT')
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def _addon_dir() -> str | None:
    """获取插件根目录的绝对路径。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _purge_cached_modules() -> None:
    """清除 aiwork 相关的缓存模块，确保重载时加载最新代码。"""
    to_remove = [name for name in sys.modules if name.startswith(__package__)]
    for name in to_remove:
        del sys.modules[name]
    log.info("已清除 %d 个缓存模块", len(to_remove))
