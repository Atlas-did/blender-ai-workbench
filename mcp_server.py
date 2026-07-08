"""
mcp_server.py — MCP Socket Server (运行在 Blender 内部)
========================================================
参考 blender-mcp 设计：在 Blender 内部启动 TCP socket 服务，
接收 JSON 命令，分发给 tools_registry 中的工具，返回 JSON 响应。

外部 MCP 客户端（Claude Code / Cursor / VS Code）通过 TCP 连接，
发送 {"type": "tool_name", "params": {...}}，收到 {"status": "success", "result": {...}}。

架构：
  外部 AI ──TCP──→ Blender:9876 ──→ tools_registry.execute_tool()
                      ↑
                 mcp_server.py
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import traceback
from typing import Any, Callable

import bpy

from .tools_registry import execute_tool, get_all_definitions, get_tool, list_tool_names

log = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876
RECV_BUFFER = 8192
MAX_BUFFER_SIZE = 1024 * 1024  # 1MB，防止恶意客户端耗尽内存
SOCKET_TIMEOUT = 1.0


class BlenderMCPServer:
    """运行在 Blender 主进程中的 TCP Socket 服务端。

    接收 JSON 格式的命令，在 Blender 主线程执行，返回结果。
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.running = False
        self._socket: socket.socket | None = None
        self._server_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """启动服务器。"""
        if self.running:
            log.info("MCP 服务器已在运行")
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.listen(2)
            self.running = True

            self._server_thread = threading.Thread(target=self._server_loop, daemon=True)
            self._server_thread.start()

            log.info(f"MCP 服务器已启动: {self.host}:{self.port}")
            return True
        except OSError as e:
            log.error(f"启动 MCP 服务器失败 (端口 {self.port} 可能被占用): {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """停止服务器。"""
        self.running = False

        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
        self._server_thread = None

        log.info("MCP 服务器已停止")

    # ------------------------------------------------------------------
    # 服务循环
    # ------------------------------------------------------------------

    def _server_loop(self) -> None:
        """主循环：接受连接，每个客户端一个线程。"""
        assert self._socket is not None
        self._socket.settimeout(SOCKET_TIMEOUT)

        while self.running:
            try:
                client, addr = self._socket.accept()
                log.info(f"MCP 客户端已连接: {addr}")
                t = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if self.running:
                    log.exception("MCP 服务器 accept 异常")
                break

    def _handle_client(self, client: socket.socket) -> None:
        """处理单个客户端连接。"""
        client.settimeout(None)
        buffer = b""

        try:
            while self.running:
                try:
                    data = client.recv(RECV_BUFFER)
                    if not data:
                        log.info("MCP 客户端断开")
                        break

                    buffer += data
                    if len(buffer) > MAX_BUFFER_SIZE:
                        log.error("MCP buffer 溢出 (%d bytes)，关闭连接", len(buffer))
                        break
                    try:
                        command = json.loads(buffer.decode("utf-8"))
                        buffer = b""
                        self._dispatch_and_reply(client, command)
                    except json.JSONDecodeError:
                        pass  # 数据不完整，继续接收
                except OSError:
                    break
        finally:
            try:
                client.close()
            except OSError:
                pass

    def _dispatch_and_reply(self, client: socket.socket, command: dict) -> None:
        """在 Blender 主线程执行命令，然后回复。"""

        def _exec() -> None:
            try:
                result = self._execute_command(command)
                response = json.dumps(result, ensure_ascii=False)
                try:
                    client.sendall(response.encode("utf-8"))
                except OSError:
                    log.warning("发送响应失败，客户端可能已断开")
            except Exception as exc:
                log.exception("执行 MCP 命令失败")
                error_resp = json.dumps(
                    {"status": "error", "message": str(exc)}, ensure_ascii=False
                )
                try:
                    client.sendall(error_resp.encode("utf-8"))
                except OSError:
                    pass

        # 通过 Blender timer 在主线程执行
        bpy.app.timers.register(_exec, first_interval=0.0)

    # ------------------------------------------------------------------
    # 命令分发
    # ------------------------------------------------------------------

    def _execute_command(self, command: dict) -> dict:
        """分发命令到对应的处理器。"""
        cmd_type = command.get("type", "")
        params = command.get("params", {})

        # 元命令
        if cmd_type == "list_tools":
            return self._handle_list_tools()
        if cmd_type == "get_tool_info":
            return self._handle_get_tool_info(params)
        if cmd_type == "ping":
            return {"status": "success", "result": "pong"}

        # 工具调用 —— 统一走 tools_registry
        return self._handle_tool_call(cmd_type, params)

    # ------------------------------------------------------------------
    # 元命令处理
    # ------------------------------------------------------------------

    def _handle_list_tools(self) -> dict:
        """列出所有可用工具。"""
        defs = get_all_definitions()
        tools = []
        for d in defs:
            tools.append({
                "name": d.name,
                "description": d.description,
                "parameters": [
                    {"name": p.name, "type": p.param_type, "description": p.description, "required": p.required}
                    for p in d.parameters
                ],
                "risk_level": d.risk_level.value,
            })
        return {"status": "success", "result": {"tools": tools}}

    def _handle_get_tool_info(self, params: dict) -> dict:
        """获取单个工具的详细信息。"""
        name = params.get("name", "")
        entry = get_tool(name)
        if not entry:
            return {"status": "error", "message": f"未知工具: {name}"}
        d = entry["definition"]
        return {"status": "success", "result": {
            "name": d.name,
            "description": d.description,
            "parameters": [
                {"name": p.name, "type": p.param_type, "description": p.description, "required": p.required}
                for p in d.parameters
            ],
            "risk_level": d.risk_level.value,
        }}

    def _handle_tool_call(self, name: str, params: dict) -> dict:
        """执行工具调用（通过 tools_registry）。"""
        try:
            result = execute_tool(name, params)
            return {"status": "success", "result": result}
        except ValueError as e:
            return {"status": "error", "message": str(e)}
        except Exception as e:
            log.exception(f"MCP 工具 '{name}' 执行异常")
            return {"status": "error", "message": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_server: BlenderMCPServer | None = None


def get_server() -> BlenderMCPServer:
    global _server
    if _server is None:
        _server = BlenderMCPServer()
    return _server


def start_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    srv = get_server()
    srv.host = host
    srv.port = port
    return srv.start()


def stop_server() -> None:
    srv = get_server()
    srv.stop()


def is_running() -> bool:
    return _server is not None and _server.running
