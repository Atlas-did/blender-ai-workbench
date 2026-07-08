"""
service_stream.py — 流式响应接收与分片更新
===========================================
处理 LLM 的 SSE / 流式响应：
- 分片接收 token
- 逐字更新 UI
- 处理 [DONE] 信号
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)
