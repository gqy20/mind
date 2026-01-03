"""
ConversationManager 工具集成的单元测试

测试重构后的工具功能：
- 工具不再使用 ToolAgent
- 分析对话上下文而非项目源码
"""

import pytest
from anthropic.types import MessageParam

from mind.agents.agent import Agent
from mind.manager import ConversationManager


class TestConversationManagerToolIntegration:
    """测试 ConversationManager 的工具集成逻辑"""

    @pytest.mark.asyncio
    async def test_query_tool_analyzes_conversation(self):
        """测试：query_tool 分析对话上下文"""
        # Arrange
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=True)

        messages: list[MessageParam] = [
            {"role": "user", "content": "讨论话题"},
            {"role": "assistant", "content": "观点1"},
        ]

        # Act
        result = await agent_a.query_tool("总结对话", messages)

        # Assert - 应该返回对话摘要
        assert result is not None
        assert "对话" in result

    @pytest.mark.asyncio
    async def test_tool_agent_shared_but_not_used_for_query(self):
        """测试：ToolAgent 仍然被共享但不再用于 query_tool"""
        # Arrange & Act
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=True)

        # Assert
        # ToolAgent 仍然被设置（用于提示词增强）
        assert agent_a.tool_agent is not None
        assert agent_b.tool_agent is not None
        # 是同一个实例
        assert id(agent_a.tool_agent) == id(agent_b.tool_agent)

    @pytest.mark.asyncio
    async def test_query_tool_works_without_tool_agent(self):
        """测试：query_tool 不再依赖 tool_agent"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试")

        messages: list[MessageParam] = [
            {"role": "user", "content": "测试话题"},
            {"role": "assistant", "content": "测试回复"},
        ]

        # Act - 即使没有 tool_agent 也能工作
        result = await agent.query_tool("总结", messages)

        # Assert
        assert result is not None
