"""测试 AnthropicClient API 通信封装"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_client_init():
    """测试客户端初始化"""
    from mind.agents.client import AnthropicClient

    client = AnthropicClient(
        model="claude-sonnet-4-5-20250929",
        api_key="test-key",
    )

    assert client.model == "claude-sonnet-4-5-20250929"


@pytest.mark.asyncio
async def test_client_stream_returns_events():
    """测试 stream 方法返回事件流"""
    from mind.agents.client import AnthropicClient

    # Mock 响应事件
    mock_event = MagicMock()
    mock_event.type = "text"

    # 创建模拟的流迭代器
    async def mock_iter():
        yield mock_event

    # 创建模拟的流上下文
    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    # 创建模拟的客户端
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

        events = []
        async for event in client.stream(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful",
        ):
            events.append(event)

    assert len(events) == 1
    assert events[0].type == "text"
