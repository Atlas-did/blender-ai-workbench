"""
mcp_client.py — MCP (Model Context Protocol) 通信封装
======================================================
负责与 MCP 服务端的通信。
MCP 让 AI 能直接调用 Blender 的工具，而不经过中间层翻译。

当前为骨架，后续补全协议实现。
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


async def connect(server_address: str) -> bool:
    """连接到 MCP 服务器。

    TODO: 实现 MCP 握手协议。
    """
    log.info("MCP 客户端: 连接 %s (骨架)", server_address)
    return False


async def list_tools(server_address: str) -> list[dict]:
    """列出 MCP 服务器提供的工具。

    TODO: 实现 tools/list 请求。
    """
    log.info("MCP 客户端: 列出工具 (骨架)")
    return []


async def call_tool(server_address: str, tool_name: str, arguments: dict) -> dict:
    """调用 MCP 服务器的工具。

    TODO: 实现 tools/call 请求。
    """
    log.info("MCP 客户端: 调用 %s (骨架)", tool_name)
    return {"error": "MCP 客户端尚未实现"}
