"""
ConversationManager 工具集成的单元测试

测试 ConversationManager 的工具能力：
- enable_tools 参数配置
- 为智能体设置工具
- 工具调用时机
"""

from unittest.mock import patch

import pytest

from mind.agent import Agent
from mind.conversation import ConversationManager


class TestConversationManagerEnableTools:
    """测试 ConversationManager 的 enable_tools 参数"""

    def test_init_with_enable_tools_false(self):
        """测试：enable_tools=False 时不设置工具"""
        # Arrange & Act
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=False)

        # Assert
        assert agent_a.tool_agent is None
        assert agent_b.tool_agent is None

    def test_init_with_enable_tools_true(self):
        """测试：enable_tools=True 时设置工具"""
        # Arrange
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")

        # Act
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=True)

        # Assert
        assert agent_a.tool_agent is not None
        assert agent_b.tool_agent is not None
        # 两个智能体共享同一个 ToolAgent 实例
        assert agent_a.tool_agent is agent_b.tool_agent

    def test_init_default_enable_tools_is_false(self):
        """测试：默认 enable_tools=False"""
        # Arrange & Act
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Assert
        assert agent_a.tool_agent is None
        assert agent_b.tool_agent is None


class TestConversationManagerToolIntegration:
    """测试 ConversationManager 的工具集成逻辑"""

    @pytest.mark.asyncio
    async def test_query_tool_in_conversation_context(self):
        """测试：在对话上下文中调用工具"""
        # Arrange
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=True)

        # Mock ToolAgent.analyze_codebase
        mock_result = {
            "success": True,
            "summary": "代码库概述",
            "structure": "结构",
            "error": None,
        }

        with patch.object(
            agent_a.tool_agent, "analyze_codebase", return_value=mock_result
        ):
            # Act
            result = await agent_a.query_tool("分析代码库")

        # Assert
        assert result == "代码库概述"

    @pytest.mark.asyncio
    async def test_tool_agent_is_shared_between_agents(self):
        """测试：工具智能体在两个智能体之间共享"""
        # Arrange & Act
        agent_a = Agent(name="AgentA", system_prompt="提示A")
        agent_b = Agent(name="AgentB", system_prompt="提示B")
        _ = ConversationManager(agent_a=agent_a, agent_b=agent_b, enable_tools=True)

        # Assert
        # 检查是同一个实例
        assert id(agent_a.tool_agent) == id(agent_b.tool_agent)
