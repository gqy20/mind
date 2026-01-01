"""
Agent 工具扩展功能的单元测试

测试 Agent 类的工具能力：
- 可选的 tool_agent 属性
- query_tool() 方法
- 错误处理
"""

from unittest.mock import patch

import pytest

from mind.agent import Agent
from mind.tools import ToolAgent


class TestAgentToolAgentAttribute:
    """测试 Agent 的 tool_agent 属性"""

    def test_init_without_tool_agent(self):
        """测试：不传 tool_agent 时，属性应为 None"""
        # Arrange & Act
        agent = Agent(name="TestAgent", system_prompt="测试提示")

        # Assert
        assert agent.tool_agent is None

    def test_init_with_tool_agent(self):
        """测试：传入 ToolAgent 实例时应正确设置"""
        # Arrange
        tool_agent = ToolAgent()

        # Act
        agent = Agent(
            name="TestAgent",
            system_prompt="测试提示",
            tool_agent=tool_agent,
        )

        # Assert
        assert agent.tool_agent is tool_agent
        assert agent.tool_agent is not None


class TestAgentQueryTool:
    """测试 Agent 的 query_tool 方法"""

    @pytest.mark.asyncio
    async def test_query_tool_without_tool_agent_returns_none(self):
        """测试：没有 tool_agent 时应返回 None"""
        # Arrange
        agent = Agent(name="TestAgent", system_prompt="测试提示")

        # Act
        result = await agent.query_tool("分析代码库")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_query_tool_with_tool_agent_returns_result(self):
        """测试：有 tool_agent 时应返回分析结果"""
        # Arrange
        tool_agent = ToolAgent()

        # Mock analyze_codebase 方法
        mock_result = {
            "success": True,
            "summary": "代码库概述：这是一个测试项目",
            "structure": "项目结构...",
            "error": None,
        }

        with patch.object(
            tool_agent, "analyze_codebase", return_value=mock_result
        ) as mock_analyze:
            # Act
            agent = Agent(
                name="TestAgent",
                system_prompt="测试提示",
                tool_agent=tool_agent,
            )
            result = await agent.query_tool("分析代码库")

        # Assert
        assert result == "代码库概述：这是一个测试项目"
        mock_analyze.assert_called_once_with(".")

    @pytest.mark.asyncio
    async def test_query_tool_handles_tool_error_gracefully(self):
        """测试：工具调用失败时应返回 None"""
        # Arrange
        tool_agent = ToolAgent()

        error_result = {
            "success": False,
            "summary": "",
            "structure": "",
            "error": "CLI not found",
        }

        with patch.object(tool_agent, "analyze_codebase", return_value=error_result):
            # Act
            agent = Agent(
                name="TestAgent",
                system_prompt="测试提示",
                tool_agent=tool_agent,
            )
            result = await agent.query_tool("分析代码库")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_query_tool_handles_exception_gracefully(self):
        """测试：工具抛出异常时应返回 None"""
        # Arrange
        tool_agent = ToolAgent()

        with patch.object(
            tool_agent, "analyze_codebase", side_effect=Exception("工具异常")
        ):
            # Act
            agent = Agent(
                name="TestAgent",
                system_prompt="测试提示",
                tool_agent=tool_agent,
            )
            result = await agent.query_tool("分析代码库")

        # Assert
        assert result is None
