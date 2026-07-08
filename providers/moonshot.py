"""Moonshot (Kimi) Provider。"""

from __future__ import annotations

import json
from typing import Any

from .base import BaseProvider, ProviderInfo


class MoonshotProvider(BaseProvider):
    info = ProviderInfo(
        provider_id="moonshot",
        display_name="Moonshot (Kimi)",
        description="月之暗面 Kimi — 131K 上下文",
        default_endpoint="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-auto",
        default_api_key_env="MOONSHOT_API_KEY",
    )

    def list_models(self) -> list[str]:
        return [
            "moonshot-v1-auto",
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
        ]

    def build_request(self, messages, model, *, max_tokens=4096, temperature=0.7, tools=None, stream=True):
        url = self.info.default_endpoint.rstrip("/") + "/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "",  # 由调用方注入
        }
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        return url, headers, body

    def parse_stream_chunk(self, chunk: dict) -> dict | None:
        choices = chunk.get("choices", [])
        if not choices:
            return None
        choice = choices[0]
        delta = choice.get("delta", {})
        return {
            "content": delta.get("content", ""),
            "tool_calls": delta.get("tool_calls"),
            "finish_reason": choice.get("finish_reason"),
        }

    def parse_tool_calls_from_chunks(self, chunks: list[dict]) -> list[dict]:
        buffers: dict[int, dict] = {}
        for chunk in chunks:
            parsed = self.parse_stream_chunk(chunk)
            if not parsed:
                continue
            tc_deltas = parsed.get("tool_calls") or []
            for dtc in tc_deltas:
                idx = dtc.get("index", 0)
                if idx not in buffers:
                    buffers[idx] = {"id": dtc.get("id", ""), "name": "", "arguments_str": ""}
                buf = buffers[idx]
                func = dtc.get("function", {})
                if func.get("name"):
                    buf["name"] = func["name"]
                if func.get("arguments"):
                    buf["arguments_str"] += func["arguments"]

        result = []
        for buf in buffers.values():
            try:
                args = json.loads(buf["arguments_str"]) if buf["arguments_str"] else {}
            except json.JSONDecodeError:
                args = {}
            result.append({"id": buf.get("id", ""), "name": buf["name"], "arguments": args})
        return result

    def validate_api_key(self, api_key: str) -> bool:
        return bool(api_key) and api_key.startswith("sk-")

    def test_connection(self, endpoint: str, api_key: str, model: str, timeout: int = 10) -> tuple[bool, str]:
        import ssl
        import urllib.request

        url = (endpoint or self.info.default_endpoint).rstrip("/") + "/chat/completions"
        body = json.dumps({
            "model": model or self.info.default_model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
                data = json.loads(resp.read())
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                return True, f"连接成功 ({content[:30]}…)"
        except Exception as e:
            return False, str(e)
