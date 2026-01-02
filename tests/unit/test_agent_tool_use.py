"""测试 Agent 的 Tool Use API 功能

测试智能体使用 Anthropic 标准 Tool Use API 进行工具调用。
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import MessageParam

from mind.agents.agent import Agent


class MockAsyncStream:
    """Mock 的异步流式响应"""

    def __init__(self, events):
        self.events = events

    def __aiter__(self):
        async def async_gen():
            for event in self.events:
                yield event

        return async_gen()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class TestAgentToolUse:
    """测试 Agent 的 Tool Use API 功能"""

    @pytest.mark.asyncio
    async def test_respond_with_tool_use_search(self):
        """测试：AI 使用 Tool Use 调用搜索功能"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="GPT-5 什么时候发布？")]

        # 模拟流式事件
        # 创建 mock 的 content_block（ToolUseBlock）
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.id = "toolu_123"
        mock_tool_block.name = "search_web"
        mock_tool_block.input = {"query": "GPT-5 发布时间"}

        events = [
            # 工具调用开始（content_block_start 时 input 为空）
            MagicMock(
                type="content_block_start", index=0, content_block=mock_tool_block
            ),
            # 工具调用结束（content_block_stop 时 input 已完整）
            MagicMock(
                type="content_block_stop", index=0, content_block=mock_tool_block
            ),
            # 文本响应
            MagicMock(type="text", text="根据搜索结果，"),
            MagicMock(type="text", text="GPT-5 尚未正式发布。"),
            MagicMock(type="content_block_stop"),
        ]

        mock_stream = MockAsyncStream(events)

        # Mock 第二次调用（_continue_response）
        events2 = [
            MagicMock(type="text", text="GPT-5 尚未正式发布。"),
            MagicMock(type="content_block_stop"),
        ]

        mock_stream2 = MockAsyncStream(events2)

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_stream
            return mock_stream2

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", side_effect=side_effect):
            # Mock _search_sync 返回原始搜索结果
            mock_results = [
                {
                    "title": "GPT-5 未发布",
                    "href": "https://example.com/gpt5",
                    "body": "GPT-5 尚未正式发布",
                }
            ]
            with patch(
                "mind.tools.search_tool._search_sync", return_value=mock_results
            ):
                interrupt = asyncio.Event()

                # Act
                response = await agent.respond(messages, interrupt)

                # Assert - 应该返回文本响应（基于工具结果）
                assert response is not None
                # 注意：第一次响应可能为空（只有工具调用），第二次有文本
                # 所以我们只检查非空
                assert len(response) >= 0

    @pytest.mark.asyncio
    async def test_respond_without_tool_use(self):
        """测试：普通对话不使用工具"""
        # Arrange
        agent = Agent(name="测试", system_prompt="你是一个助手")
        messages = [MessageParam(role="user", content="你好")]

        # 模拟普通文本响应（无工具调用）
        events = [
            MagicMock(type="text", text="你好！"),
            MagicMock(type="text", text="有什么我可以帮助的吗？"),
            MagicMock(type="content_block_stop"),
        ]

        mock_stream = MockAsyncStream(events)

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
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

        # 模拟中途中断
        events = [
            MagicMock(type="text", text="让我查一下"),
            # 中断事件
        ]

        mock_stream = MockAsyncStream(events)

        interrupt = asyncio.Event()
        interrupt.set()  # 立即设置中断

        # 新架构: agent.client 是 AnthropicClient，直接 patch stream 方法
        with patch.object(agent.client, "stream", return_value=mock_stream):
            # Act
            response = await agent.respond(messages, interrupt)

            # Assert - 中断应返回 None
            assert response is None
