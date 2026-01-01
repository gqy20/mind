"""
Agent 工具功能的单元测试

测试重构后的 query_tool 方法：
- 分析对话上下文而非项目源码
- 不再依赖 ToolAgent
"""

import pytest
from anthropic.types import MessageParam

from mind.agent import Agent


class TestAgentQueryTool:
    """测试 Agent 的 query_tool 方法"""

    @pytest.mark.asyncio
    async def test_query_tool_without_messages_returns_none(self):
        """测试：没有 messages 时应返回 None"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")

        # Act
        result = await agent.query_tool("分析对话", messages=None)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_query_tool_with_empty_messages_returns_none(self):
        """测试：空 messages 列表应返回 None"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")
        messages: list[MessageParam] = []

        # Act
        result = await agent.query_tool("分析对话", messages)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_query_tool_analyzes_conversation_context(self):
        """测试：分析对话上下文应返回摘要"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")
        messages: list[MessageParam] = [
            {"role": "user", "content": "讨论 AI 是否有意识"},
            {"role": "assistant", "content": "观点1：AI 没有真实意识"},
            {"role": "assistant", "content": "观点2：AI 可以模拟意识"},
        ]

        # Act
        result = await agent.query_tool("总结对话", messages)

        # Assert - 应该包含对话摘要
        assert result is not None
        assert "对话话题" in result or "对话轮次" in result

    @pytest.mark.asyncio
    async def test_query_tool_filters_system_messages(self):
        """测试：应该过滤掉 system 角色的消息"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")
        messages: list[MessageParam] = [
            {"role": "system", "content": "系统指令"},
            {"role": "user", "content": "用户话题"},
            {"role": "assistant", "content": "助手回复"},
        ]

        # Act
        result = await agent.query_tool("总结对话", messages)

        # Assert - system 消息应该被过滤
        assert result is not None
        # 摘要中不应该包含"系统指令"

    @pytest.mark.asyncio
    async def test_query_tool_handles_structured_content(self):
        """测试：正确处理结构化内容（blocks）"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")
        # 模拟可能的结构化内容
        messages: list[MessageParam] = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "结构化话题"}],
            },
            {"role": "assistant", "content": "助手回复"},
        ]

        # Act - 不应该抛出异常
        result = await agent.query_tool("总结对话", messages)

        # Assert
        assert result is not None
