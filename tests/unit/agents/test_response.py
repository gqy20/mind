"""测试 ResponseHandler 响应处理"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_response_handler_returns_text():
    """测试响应处理器返回文本"""
    from mind.agents.response import ResponseHandler

    from mind.agents.client import AnthropicClient

    # Mock 事件流
    mock_event = MagicMock()
    mock_event.type = "text"
    mock_event.text = "Hello"

    # 创建模拟的流迭代器
    async def mock_iter():
        yield mock_event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    mock_anthropic.messages.stream = MagicMock(return_value=mock_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)
        result = await handler.respond(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    assert result == "Hello"


@pytest.mark.asyncio
async def test_response_handler_interrupt_returns_none():
    """测试中断时返回 None"""
    from mind.agents.response import ResponseHandler

    from mind.agents.client import AnthropicClient

    interrupt = asyncio.Event()
    interrupt.set()

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")

        handler = ResponseHandler(client)
        result = await handler.respond(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful",
            interrupt=interrupt,
        )

    assert result is None
