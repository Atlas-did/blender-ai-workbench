"""
service_worker.py — 后台任务与异步执行
=======================================
处理需要在后台线程执行的任务，避免阻塞 Blender UI：
- LLM API 调用
- 长时间工具执行
- 文件批量处理
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)
