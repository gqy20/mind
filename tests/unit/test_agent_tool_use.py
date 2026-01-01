"""测试 Agent 的 Tool Use API 功能

测试智能体使用 Anthropic 标准 Tool Use API 进行工具调用。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import MessageParam

from mind.agent import Agent


class TestAgentToolUse:
    """测试 Agent 的 Tool Use API 功能"""

    @pytest.mark.asyncio
    async def test_respond_with_tool_use_search(self):
        """测试：AI 使用 Tool Use 调用搜索功能"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="GPT-5 什么时候发布？")]

        # 模拟 API 返回工具调用
        mock_response = MagicMock()
        mock_stream = AsyncMock()

        # 模拟流式事件
        events = [
            MagicMock(type="content_block_start", index=0),
            # 工具调用开始
            MagicMock(
                type="tool_use",
                name="search_web",
                id="toolu_123",
                input={"query": "GPT-5 发布时间"},
            ),
            # 工具调用结束
            MagicMock(type="content_block_stop", index=0),
            # 文本响应
            MagicMock(type="text", text="根据搜索结果，"),
            MagicMock(type="text", text="GPT-5 尚未正式发布。"),
            MagicMock(type="content_block_stop"),
        ]

        mock_stream.__aiter__ = AsyncMock(return_value=iter(events))
        mock_response.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(agent.client.messages, "stream", return_value=mock_response):
            with patch(
                "mind.tools.search_tool.search_web", return_value="GPT-5 未发布"
            ):
                interrupt = asyncio.Event()

                # Act
                response = await agent.respond(messages, interrupt)

                # Assert - 应该返回文本响应（基于工具结果）
                assert response is not None
                assert "GPT-5" in response or "未发布" in response

    @pytest.mark.asyncio
    async def test_respond_without_tool_use(self):
        """测试：普通对话不使用工具"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="你好")]

        # 模拟普通文本响应（无工具调用）
        mock_response = MagicMock()
        mock_stream = AsyncMock()

        events = [
            MagicMock(type="text", text="你好！"),
            MagicMock(type="text", text="有什么我可以帮助的吗？"),
            MagicMock(type="content_block_stop"),
        ]

        mock_stream.__aiter__ = AsyncMock(return_value=iter(events))
        mock_response.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(agent.client.messages, "stream", return_value=mock_response):
            interrupt = asyncio.Event()

            # Act
            response = await agent.respond(messages, interrupt)

            # Assert
            assert response is not None
            assert "你好" in response

    @pytest.mark.asyncio
    async def test_tool_use_interrupted(self):
        """测试：工具调用过程中被中断"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="搜索问题")]

        mock_response = MagicMock()
        mock_stream = AsyncMock()

        # 模拟中途中断
        events = [
            MagicMock(type="text", text="让我查一下"),
            # 中断事件
        ]

        interrupt = asyncio.Event()
        interrupt.set()  # 立即设置中断

        async def mock_iter():
            for event in events:
                if interrupt.is_set():
                    break
                yield event

        mock_stream.__aiter__ = AsyncMock(side_effect=mock_iter())
        mock_response.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_response.__aexit__ = AsyncMock()

        with patch.object(agent.client.messages, "stream", return_value=mock_response):
            # Act
            response = await agent.respond(messages, interrupt)

            # Assert - 中断应返回 None
            assert response is None
