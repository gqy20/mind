"""响应处理逻辑

处理流式响应、文本累积、工具调用等。
"""

import asyncio
from typing import TYPE_CHECKING

from mind.agents.client import AnthropicClient

if TYPE_CHECKING:
    from anthropic.types import MessageParam


class ResponseHandler:
    """响应处理器 - 处理流式响应和工具调用"""

    def __init__(
        self,
        client: AnthropicClient,
        search_history=None,
    ):
        """初始化响应处理器

        Args:
            client: Anthropic API 客户端
            search_history: 可选的搜索历史记录
        """
        self.client = client
        self.search_history = search_history

    async def respond(
        self,
        messages: list["MessageParam"],
        system: str,
        interrupt: asyncio.Event,
    ) -> str | None:
        """生成响应

        Args:
            messages: 对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            完整响应文本，如果被中断则返回 None
        """
        if interrupt.is_set():
            return None

        response_text = ""
        tool_use_buffer: list[dict] = []
        citations_buffer: list[dict] = []

        try:
            # 第一轮：生成响应
            async for event in self.client.stream(
                messages=messages,
                system=system,
                tools=_get_tools_schema(),
            ):
                if interrupt.is_set():
                    return None

                # 处理旧格式文本事件
                if event.type == "text":
                    text = getattr(event, "text", "")
                    response_text += text
                    print(text, end="", flush=True)

                # 处理文本增量
                elif event.type == "content_block_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "text"):
                        text = event.delta.text
                        response_text += text
                        print(text, end="", flush=True)

                # 处理引用增量
                elif event.type == "content_block_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "citations"):
                        for citation in event.delta.citations:
                            citations_buffer.append(
                                {
                                    "type": getattr(citation, "type", "unknown"),
                                    "document_title": getattr(
                                        citation, "document_title", "未知来源"
                                    ),
                                    "cited_text": getattr(citation, "cited_text", ""),
                                }
                            )

                # 处理工具调用
                elif event.type == "content_block_stop":
                    if hasattr(event, "content_block"):
                        block = event.content_block
                        if block.type == "tool_use":
                            tool_use_buffer.append(
                                {
                                    "id": getattr(block, "id", ""),
                                    "name": getattr(block, "name", ""),
                                    "input": getattr(block, "input", {}),
                                }
                            )

        except Exception:
            # 错误处理 - 返回已累积的文本
            pass

        # TODO: 处理工具调用
        # TODO: 显示引用

        return response_text


def _get_tools_schema() -> list:
    """获取可用工具的 schema 定义

    Returns:
        工具 schema 列表
    """
    return [
        {
            "name": "search_web",
            "description": "搜索网络信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    },
                },
                "required": ["query"],
            },
        }
    ]
