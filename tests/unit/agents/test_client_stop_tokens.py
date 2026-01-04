"""测试 AnthropicClient 的 stop_tokens 功能

测试验证 client 可以正确传递 stop_sequences 参数到 API。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestStopTokens:
    """测试 stop_tokens 功能"""

    def test_client_accepts_stop_tokens(self):
        """测试客户端接受 stop_tokens 参数"""
        from mind.agents.client import AnthropicClient

        # Mock 客户端
        with patch("mind.agents.client.AsyncAnthropic"):
            client = AnthropicClient(model="test-model", api_key="test-key")

            # 验证客户端实例化成功
            assert client.model == "test-model"
            assert client.api_key == "test-key"

    @pytest.mark.asyncio
    async def test_stream_passes_stop_tokens_to_api(self):
        """测试 stream 方法不传 stop_tokens 时不添加 stop_sequences"""
        from mind.agents.client import AnthropicClient

        # 创建空的异步生成器作为 mock
        async def empty_stream():
            yield  # type: ignore[misc]
            return

        # Mock stream 上下文管理器
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=empty_stream())
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: empty_stream()

        # 注意：现在使用 beta.messages.stream 而不是 messages.stream
        mock_beta_messages = MagicMock()
        mock_beta_messages.stream.return_value = mock_stream

        mock_client = MagicMock()
        mock_client.beta.messages = mock_beta_messages

        with patch("mind.agents.client.AsyncAnthropic", return_value=mock_client):
            client = AnthropicClient(model="test-model", api_key="test-key")

            # 调用 stream，不传 stop_tokens
            async for _ in client.stream(
                messages=[{"role": "user", "content": "test"}],
                system="test system",
            ):
                pass

            # 验证调用时没有 stop_sequences
            call_kwargs = mock_beta_messages.stream.call_args[1]
            assert "stop_sequences" not in call_kwargs

    @pytest.mark.asyncio
    async def test_stream_with_stop_tokens_parameter(self):
        """测试 stream 方法正确传递 stop_tokens 参数"""
        from mind.agents.client import AnthropicClient

        # 创建空的异步生成器作为 mock
        async def empty_stream():
            yield  # type: ignore[misc]
            return

        # Mock stream 上下文管理器
        mock_stream = MagicMock()
        mock_stream.__aenter__ = AsyncMock(return_value=empty_stream())
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: empty_stream()

        # 注意：现在使用 beta.messages.stream 而不是 messages.stream
        mock_beta_messages = MagicMock()
        mock_beta_messages.stream.return_value = mock_stream

        mock_client = MagicMock()
        mock_client.beta.messages = mock_beta_messages

        with patch("mind.agents.client.AsyncAnthropic", return_value=mock_client):
            client = AnthropicClient(model="test-model", api_key="test-key")

            # 定义 stop_tokens
            stop_tokens = ["<thinking>", "</thinking>"]

            # 调用 stream，传递 stop_tokens
            async for _ in client.stream(
                messages=[{"role": "user", "content": "test"}],
                system="test system",
                stop_tokens=stop_tokens,
            ):
                pass

            # 验证 stop_sequences 被正确传递
            call_kwargs = mock_beta_messages.stream.call_args[1]
            assert "stop_sequences" in call_kwargs
            assert call_kwargs["stop_sequences"] == stop_tokens
