"""Anthropic API 客户端封装

只负责与 Anthropic API 通信，不处理业务逻辑。
"""

import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolParam

if TYPE_CHECKING:
    Event = Any  # API 返回的事件类型


class AnthropicClient:
    """Anthropic API 客户端封装"""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """初始化客户端

        Args:
            model: 使用的模型名称
            api_key: API 密钥，默认从环境变量读取
            base_url: API 基础 URL（可选，用于代理等场景）
        """
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")

        if base_url:
            self.client = AsyncAnthropic(api_key=self.api_key, base_url=base_url)
        else:
            self.client = AsyncAnthropic(api_key=self.api_key)

    async def stream(
        self,
        messages: list[MessageParam],
        system: str,
        tools: list[ToolParam] | None = None,
        documents: list | None = None,
    ) -> AsyncIterator["Event"]:
        """流式生成 - 返回原始事件流

        Args:
            messages: 对话历史
            system: 系统提示词
            tools: 可用的工具定义
            documents: Citations API 文档列表

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

        async with self.client.messages.stream(**kwargs) as stream:  # type: ignore[arg-type]
            async for event in stream:
                yield event
