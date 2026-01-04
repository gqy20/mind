"""Anthropic API 客户端封装

只负责与 Anthropic API 通信，不处理业务逻辑。
"""

import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolParam

if TYPE_CHECKING:
    Event = Any  # API 返回的事件类型

# Timeout 类型可以是 float（秒数）或 httpx.Timeout 对象
Timeout = float | httpx.Timeout


class AnthropicClient:
    """Anthropic API 客户端封装"""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 2,
        timeout: Timeout | None = None,
    ):
        """初始化客户端

        Args:
            model: 使用的模型名称
            api_key: API 密钥，默认从环境变量读取
            base_url: API 基础 URL（可选，用于代理等场景）
            max_retries: 最大重试次数，默认 2（anthropic 库默认值）
            timeout: 请求超时配置，可以是秒数（float）或 httpx.Timeout 对象
        """
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")

        # 构建 AsyncAnthropic 参数
        client_kwargs: dict[str, Any] = {"api_key": self.api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if max_retries != 2:  # 只在非默认值时传递
            client_kwargs["max_retries"] = max_retries
        if timeout is not None:
            client_kwargs["timeout"] = timeout

        self.client = AsyncAnthropic(**client_kwargs)

    async def stream(
        self,
        messages: list[MessageParam],
        system: str,
        tools: list[ToolParam] | None = None,
        documents: list | None = None,
        stop_tokens: list[str] | None = None,
    ) -> AsyncIterator["Event"]:
        """流式生成 - 返回原始事件流

        Args:
            messages: 对话历史
            system: 系统提示词
            tools: 可用的工具定义
            documents: Citations API 文档列表
            stop_tokens: 停止序列，遇到这些标记时停止生成

        Yields:
            API 返回的原始事件
        """
        # 构建基本参数
        kwargs = {
            "model": self.model,
            "max_tokens": 2048,
            "system": system,
            "messages": messages,
            "tools": tools or [],
        }

        # 只有在有 documents 时才添加该参数
        if documents:
            kwargs["documents"] = documents

        # 添加 stop_sequences（如果提供）
        if stop_tokens:
            kwargs["stop_sequences"] = stop_tokens

        async with self.client.messages.stream(**kwargs) as stream:  # type: ignore[arg-type]
            async for event in stream:
                yield event
