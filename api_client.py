"""
api_client.py — LLM API 通信封装
=================================
OpenAI 兼容 API 的 HTTP 通信（Kimi / Ollama / vLLM 等）。

Blender 不自带 requests 库，使用标准库 urllib 实现。
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from typing import Any, Callable

from .schemas import ToolDefinition

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
API_CHAT_PATH = "/chat/completions"
SSE_DATA_PREFIX = b"data: "
SSE_DONE_TOKEN = b"[DONE]"


# ---------------------------------------------------------------------------
# 构建请求体
# ---------------------------------------------------------------------------

def _build_request_body(
    messages: list[dict[str, Any]],
    model: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.7,
    tools: list[dict[str, Any]] | None = None,
    stream: bool = False,
    tool_choice: str = "auto",
) -> dict[str, Any]:
    """构建 OpenAI 兼容的请求体。"""
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice
    return body


def messages_to_api(
    messages: list[dict[str, Any]],
    system_prompt: str = "",
) -> list[dict[str, Any]]:
    """把内部消息列表转为 API 格式，可选插入 system prompt。"""
    api_msgs: list[dict[str, Any]] = []
    if system_prompt:
        api_msgs.append({"role": "system", "content": system_prompt})
    api_msgs.extend(messages)
    return api_msgs


def tool_def_to_api(tool: ToolDefinition) -> dict[str, Any]:
    """把 ToolDefinition 转为 OpenAI function 格式。"""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in tool.parameters:
        type_map = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "object": "object",
            "array": "array",
        }
        properties[param.name] = {
            "type": type_map.get(param.param_type, "string"),
            "description": param.description,
        }
        if param.required:
            required.append(param.name)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


# ---------------------------------------------------------------------------
# HTTP 传输
# ---------------------------------------------------------------------------

def _make_request(
    endpoint: str,
    body: dict[str, Any],
    api_key: str,
    timeout: int = 120,
) -> bytes:
    """发送 POST 请求，返回响应体 bytes。"""
    url = endpoint.rstrip("/") + API_CHAT_PATH
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        log.error("API HTTP %s: %s", e.code, error_body[:500])
        raise RuntimeError(f"API 请求失败 ({e.code}): {error_body[:300]}") from e
    except Exception:
        log.exception("API 请求异常")
        raise


# ---------------------------------------------------------------------------
# 同步聊天（非流式）
# ---------------------------------------------------------------------------

def chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str = "",
    endpoint: str = "",
    api_key: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    tools: list[dict[str, Any]] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    """同步聊天请求，返回完整响应。

    Returns:
        {
            "content": str,
            "tool_calls": [{"name": str, "arguments": dict}, ...],
            "finish_reason": str,
        }
    """
    body = _build_request_body(
        messages, model,
        max_tokens=max_tokens, temperature=temperature,
        tools=tools, stream=False,
    )
    log.info("API 请求: model=%s messages=%d tools=%d", model, len(messages), len(tools or []))

    raw = _make_request(endpoint, body, api_key, timeout=timeout)
    resp = json.loads(raw)

    choice = resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "") or ""

    # 解析 tool_calls
    raw_tool_calls = message.get("tool_calls", [])
    tool_calls = []
    for tc in raw_tool_calls:
        func = tc.get("function", {})
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({"name": func.get("name", ""), "arguments": args})

    result = {
        "content": content,
        "tool_calls": tool_calls,
        "finish_reason": choice.get("finish_reason", "stop"),
        "usage": resp.get("usage", {}),
    }
    log.info("API 响应: content=%d chars, tool_calls=%d, finish=%s",
             len(content), len(tool_calls), result["finish_reason"])
    return result


# ---------------------------------------------------------------------------
# 流式聊天
# ---------------------------------------------------------------------------

def chat_completion_stream(
    messages: list[dict[str, Any]],
    *,
    model: str = "",
    endpoint: str = "",
    api_key: str = "",
    max_tokens: int = 4096,
    temperature: float = 0.7,
    tools: list[dict[str, Any]] | None = None,
    timeout: int = 120,
    on_token: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
    on_done: Callable[[str, list, dict], None] | None = None,
) -> None:
    """流式聊天请求，通过回调函数逐步输出。

    Args:
        on_token: 收到新 token 时调用，参数 (delta_content: str)
        on_tool_call: 解析完一个 tool_call 时调用 (name, arguments)
        on_done: 流结束时调用 (full_content, tool_calls, usage)
    """
    body = _build_request_body(
        messages, model,
        max_tokens=max_tokens, temperature=temperature,
        tools=tools, stream=True,
    )
    log.info("API 流式请求: model=%s messages=%d", model, len(messages))

    url = endpoint.rstrip("/") + API_CHAT_PATH
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    ctx = ssl.create_default_context()

    full_content = ""
    tool_calls: list[dict] = []
    tool_call_buffers: dict[int, dict] = {}  # index → {name, arguments_str}

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            # 逐行读取 SSE 流
            line: bytes
            for line in resp:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith(SSE_DATA_PREFIX):
                    payload = stripped[len(SSE_DATA_PREFIX):]
                    if payload == SSE_DONE_TOKEN:
                        break

                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        log.warning("SSE JSON 解析失败: %.100s", payload.decode(errors="replace"))
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})

                    # 文本 delta
                    delta_content = delta.get("content", "")
                    if delta_content:
                        full_content += delta_content
                        if on_token:
                            on_token(delta_content)

                    # 工具调用 delta
                    delta_tools = delta.get("tool_calls", [])
                    for dtc in delta_tools:
                        idx = dtc.get("index", 0)
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {"id": dtc.get("id", ""), "name": "", "arguments_str": ""}
                        buf = tool_call_buffers[idx]
                        func = dtc.get("function", {})
                        if func.get("name"):
                            buf["name"] = func["name"]
                        if func.get("arguments"):
                            buf["arguments_str"] += func["arguments"]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        log.error("API HTTP %s: %s", e.code, error_body[:500])
        raise RuntimeError(f"API 请求失败 ({e.code}): {error_body[:300]}") from e
    except Exception:
        log.exception("API 流式请求异常")
        raise

    # 解析 tool_calls
    for buf in tool_call_buffers.values():
        try:
            args = json.loads(buf["arguments_str"]) if buf["arguments_str"] else {}
        except json.JSONDecodeError:
            log.warning("tool_call arguments JSON 解析失败: %s", buf["arguments_str"][:100])
            args = {}
        tc = {"name": buf["name"], "arguments": args}
        tool_calls.append(tc)
        if on_tool_call:
            on_tool_call(buf["name"], args)

    log.info("API 流完成: content=%d chars, tool_calls=%d", len(full_content), len(tool_calls))

    if on_done:
        on_done(full_content, tool_calls, {})


# ---------------------------------------------------------------------------
# 连接检查
# ---------------------------------------------------------------------------

def check_connection(endpoint: str, api_key: str = "", model: str = "", timeout: int = 10) -> tuple[bool, str]:
    """测试 LLM API 连接。

    Returns:
        (connected, message)
    """
    try:
        result = chat_completion(
            [{"role": "user", "content": "Hi"}],
            model=model or "moonshot-v1-auto",
            endpoint=endpoint,
            api_key=api_key,
            max_tokens=10,
            timeout=timeout,
        )
        return True, f"连接成功 (模型响应: {result['content'][:50]}…)"
    except Exception as e:
        return False, str(e)
