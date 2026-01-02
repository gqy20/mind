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

    # Mock 响应
    mock_event = MagicMock()
    mock_event.type = "text"
    mock_event.text = "Hello"

    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [mock_event]

    mock_client = AsyncMock()
    mock_client.messages.stream.return_value.__aenter__.return_value = mock_stream

    with patch("mind.agents.client.AsyncAnthropic", return_value=mock_client):
        client = AnthropicClient(model="test-model", api_key="test-key")
        events = []
        async for event in client.stream(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful",
        ):
            events.append(event)

    assert len(events) == 1
    assert events[0].type == "text"
