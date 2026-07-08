"""
providers/ — LLM Provider 抽象层
=================================
参考 BlenderAIStudio 的 studio/providers/ 的 Builder/Parser 模式。

每个 Provider 封装:
- 端点地址
- 可用模型列表
- 请求构建 (Builder)
- 响应解析 (Parser)
- API Key 校验

注册方式:
    from .registry import register_provider
    register_provider(MoonshotProvider())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderInfo:
    """Provider 元信息。"""
    provider_id: str          # 唯一标识, 如 "moonshot", "openai", "ollama"
    display_name: str         # 显示名称, 如 "Moonshot (Kimi)"
    description: str = ""
    default_endpoint: str = ""
    default_model: str = ""
    default_api_key_env: str = ""  # 环境变量名, 如 "MOONSHOT_API_KEY"


class BaseProvider:
    """LLM Provider 的抽象基类。"""

    info: ProviderInfo

    # ------------------------------------------------------------------
    # 模型
    # ------------------------------------------------------------------

    def list_models(self) -> list[str]:
        """返回该 Provider 当前可用的模型 ID 列表。"""
        raise NotImplementedError

    def get_default_model(self) -> str:
        return self.info.default_model

    # ------------------------------------------------------------------
    # 请求
    # ------------------------------------------------------------------

    def build_request(
        self,
        messages: list[dict[str, Any]],
        model: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
    ) -> tuple[str, dict, dict]:
        """构建请求。

        Returns:
            (url, headers, body): 请求 URL、头、体。
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 响应
    # ------------------------------------------------------------------

    def parse_stream_chunk(self, chunk: dict) -> dict | None:
        """解析单个 SSE chunk 为标准化 delta。

        Returns:
            {
                "content": str | None,
                "tool_calls": [{"index": int, "id": str, "name": str, "arguments": str}] | None,
                "finish_reason": str | None,
            }
            或 None（如果 chunk 无效）。
        """
        raise NotImplementedError

    def parse_tool_calls_from_chunks(self, chunks: list[dict]) -> list[dict]:
        """从所有 chunks 中汇总 tool_calls。

        Returns:
            [{"id": str, "name": str, "arguments": dict}, ...]
        """
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------

    def supports_vision(self, model: str) -> bool:
        """检查模型是否支持 Vision（图片输入）。"""
        return False  # 默认不支持

    def validate_api_key(self, api_key: str) -> bool:
        """校验 API Key 格式。"""
        return len(api_key) > 0

    def test_connection(self, endpoint: str, api_key: str, model: str, timeout: int = 10) -> tuple[bool, str]:
        """测试连接。

        Returns:
            (success, message)
        """
        raise NotImplementedError
