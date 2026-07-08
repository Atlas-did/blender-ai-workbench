"""
mcp_client.py — MCP 外部客户端（连接到 Blender 内的 MCP Server）
=============================================================
从外部进程（Claude Code / Cursor / VS Code / 终端脚本）连接到
Blender 内部运行的 MCP Socket Server，调用 Blender 工具。

用法示例:
    from aiwork.mcp_client import MCPClient
    client = MCPClient("localhost", 9876)
    client.connect()
    result = client.call_tool("get_scene_info")
    print(result)
    client.disconnect()

协议:
    发送: {"type": "command_name", "params": {...}}
    收到: {"status": "success", "result": {...}} 或 {"status": "error", "message": "..."}
"""

from __future__ import annotations

import json
import logging
import socket
import time
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 180.0


class MCPClient:
    """连接到 Blender MCP 服务器的 TCP 客户端。"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """建立与 Blender MCP 服务器的连接。"""
        if self.connected:
            return True
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(DEFAULT_TIMEOUT)
            self._socket.connect((self.host, self.port))
            log.info(f"已连接到 Blender MCP 服务器 {self.host}:{self.port}")
            return True
        except (ConnectionRefusedError, OSError) as e:
            log.error(f"无法连接到 Blender ({self.host}:{self.port}): {e}")
            self._socket = None
            return False

    def disconnect(self) -> None:
        """断开连接。"""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    # ------------------------------------------------------------------
    # 命令发送
    # ------------------------------------------------------------------

    def call_tool(self, name: str, params: dict | None = None) -> dict:
        """调用 Blender 中的工具。

        Args:
            name: 工具名称。
            params: 工具参数字典。

        Returns:
            {"status": "success", "result": {...}} 或 {"status": "error", "message": "..."}
        """
        return self._send_command(name, params or {})

    def ping(self) -> bool:
        """测试连接是否存活。"""
        try:
            resp = self._send_command("ping")
            return resp.get("status") == "success"
        except Exception:
            return False

    def list_tools(self) -> list[dict]:
        """列出服务器上所有可用的工具。"""
        resp = self._send_command("list_tools")
        if resp.get("status") == "success":
            return resp.get("result", {}).get("tools", [])
        return []

    def get_tool_info(self, name: str) -> dict | None:
        """获取单个工具的信息。"""
        resp = self._send_command("get_tool_info", {"name": name})
        if resp.get("status") == "success":
            return resp.get("result")
        return None

    # ------------------------------------------------------------------
    # 底层通信
    # ------------------------------------------------------------------

    def _send_command(self, cmd_type: str, params: dict | None = None) -> dict:
        """发送命令并接收完整响应。"""
        if not self.connected:
            raise ConnectionError("未连接到 Blender MCP 服务器")

        command = {"type": cmd_type, "params": params or {}}
        payload = json.dumps(command, ensure_ascii=False).encode("utf-8")

        assert self._socket is not None
        try:
            self._socket.sendall(payload)
        except OSError as e:
            self._socket = None
            raise ConnectionError(f"发送命令失败: {e}") from e

        return self._receive_full_response()

    def _receive_full_response(self) -> dict:
        """接收完整的 JSON 响应（可能分多个 chunk 到达）。"""
        assert self._socket is not None
        chunks: list[bytes] = []

        try:
            while True:
                try:
                    chunk = self._socket.recv(8192)
                except socket.timeout:
                    break
                if not chunk:
                    if not chunks:
                        raise ConnectionError("连接在收到数据前关闭")
                    break
                chunks.append(chunk)
                # 尝试解析 —— 如果成功说明收完了
                try:
                    data = b"".join(chunks)
                    result = json.loads(data.decode("utf-8"))
                    return result
                except json.JSONDecodeError:
                    continue
        except OSError as e:
            self._socket = None
            raise ConnectionError(f"接收响应失败: {e}") from e

        # 如果循环结束还没解析成功，用已有数据最后一次尝试
        if chunks:
            data = b"".join(chunks)
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                raise ConnectionError("收到不完整的 JSON 响应")
        raise ConnectionError("未收到响应数据")


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def quick_call(host: str, port: int, tool_name: str, params: dict | None = None) -> dict:
    """一次性调用：连接 → 发命令 → 断开。适合脚本使用。"""
    client = MCPClient(host, port)
    try:
        if not client.connect():
            return {"status": "error", "message": f"无法连接到 {host}:{port}"}
        return client.call_tool(tool_name, params)
    finally:
        client.disconnect()
