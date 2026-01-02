"""
Agent 类的单元测试

测试智能体的基本功能：
- 初始化配置
- 流式响应
- 中断机制
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.agents.agent import Agent


class TestAgentInit:
    """测试 Agent 初始化"""

    def test_init_with_required_params(self):
        """测试：使用必需参数初始化 Agent"""
        # Arrange & Act
        agent = Agent(name="测试智能体", system_prompt="你是一个测试助手")

        # Assert
        assert agent.name == "测试智能体"
        # system_prompt 会自动添加工具使用说明
        assert "你是一个测试助手" in agent.system_prompt
        assert agent.client is not None

    def test_init_empty_name_raises_error(self):
        """测试：空名称应抛出异常"""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="名称不能为空"):
            Agent(name="", system_prompt="提示词")


class TestAgentRespond:
    """测试 Agent 响应功能"""

    @pytest.mark.asyncio
    async def test_respond_returns_text(self):
        """测试：respond 方法应返回响应文本"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        # Mock API 响应
        async def mock_stream_iter():
            mock_event_1 = MagicMock()
            mock_event_1.type = "text"
            mock_event_1.text = "你好"
            yield mock_event_1

            mock_event_2 = MagicMock()
            mock_event_2.type = "content_block_stop"
            yield mock_event_2

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: mock_stream_iter()

        # 新架构: agent.client 是 AnthropicClient，需要 patch 其 stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result == "你好"

    @pytest.mark.asyncio
    async def test_respond_interrupted_returns_none(self):
        """测试：被中断时 respond 应返回 None"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()
        interrupt.set()  # 立即触发中断

        # Act
        result = await agent.respond(messages, interrupt)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_respond_accumulates_text_chunks(self):
        """测试：流式响应应累积所有文本块"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是助手")
        messages = [{"role": "user", "content": "你好"}]
        interrupt = asyncio.Event()

        async def mock_stream_iter():
            mock_event_1 = MagicMock()
            mock_event_1.type = "text"
            mock_event_1.text = "你好"
            yield mock_event_1

            mock_event_2 = MagicMock()
            mock_event_2.type = "text"
            mock_event_2.text = "，世界"
            yield mock_event_2

            mock_event_3 = MagicMock()
            mock_event_3.type = "text"
            mock_event_3.text = "！"
            yield mock_event_3

            mock_event_4 = MagicMock()
            mock_event_4.type = "content_block_stop"
            yield mock_event_4

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.__aiter__ = lambda self: mock_stream_iter()

        # 新架构: patch AnthropicClient.stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            result = await agent.respond(messages, interrupt)

        # Assert
        assert result == "你好，世界！"
