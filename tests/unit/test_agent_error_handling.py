"""
Agent 错误处理的单元测试

测试智能体的错误处理场景：
- API 错误
- 速率限制
- 网络超时
- 认证失败
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from anthropic import APIStatusError
from httpx import Request, Response

from mind.agents.agent import Agent


class TestAgentErrorHandling:
    """测试 Agent 错误处理"""

    def _make_error(self, status_code: int, message: str) -> APIStatusError:
        """创建 API 错误的辅助方法"""
        request = Request("POST", "https://api.anthropic.com/v1/messages")
        response = Response(
            status_code=status_code,
            request=request,
            content=f'{{"error":{{"message":"{message}"}}}}'.encode(),
        )
        return APIStatusError(  # noqa: E501
            message, response=response, body={"error": {"message": message}}
        )

    @pytest.mark.asyncio
    async def test_respond_handles_api_error_gracefully(self, capsys):
        """测试：API 错误应返回 None 并显示友好消息"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        # Mock API 抛出错误 - 需要在迭代过程中抛出
        async def error_stream_iter():
            # 在第一次迭代时抛出错误
            raise self._make_error(500, "API 请求失败")
            yield  # noqa: B901  # 使其成为异步生成器

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: error_stream_iter()

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result is None
        captured = capsys.readouterr()
        assert "错误" in captured.out

    @pytest.mark.asyncio
    async def test_respond_handles_auth_error(self, capsys):
        """测试：认证错误应显示提示"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        # Mock API 抛出错误 - 需要在迭代过程中抛出
        async def error_stream_iter():
            raise self._make_error(401, "Invalid API Key")
            yield  # noqa: B901

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: error_stream_iter()

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result is None
        captured = capsys.readouterr()
        # 应该提到认证或 API Key
        output = captured.out
        assert "错误" in output or "API" in output or "认证" in output

    @pytest.mark.asyncio
    async def test_respond_handles_rate_limit_error(self, capsys):
        """测试：速率限制应显示友好提示"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        # Mock API 抛出错误 - 需要在迭代过程中抛出
        async def error_stream_iter():
            raise self._make_error(429, "Rate limit exceeded")
            yield  # noqa: B901

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: error_stream_iter()

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result is None
        captured = capsys.readouterr()
        output = captured.out
        # 应该提示速率限制
        assert "错误" in output or "速率" in output or "限制" in output

    @pytest.mark.asyncio
    async def test_respond_handles_timeout_error(self, capsys):
        """测试：超时错误应显示提示"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        # Mock API 抛出错误 - 需要在迭代过程中抛出
        async def error_stream_iter():
            raise TimeoutError("Request timeout")
            yield  # noqa: B901

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: error_stream_iter()

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result is None
        captured = capsys.readouterr()
        assert "错误" in captured.out or "超时" in captured.out
