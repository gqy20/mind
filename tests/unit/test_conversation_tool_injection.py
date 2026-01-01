"""
ConversationManager 工具结果注入功能的单元测试

测试工具调用并将结果注入到对话历史：
- 固定间隔调用工具
- 工具结果注入到 messages
- 工具结果保存到 memory
- 禁用工具时不调用
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mind.agent import Agent
from mind.conversation import ConversationManager
from mind.tools import ToolAgent


class TestToolInjectionConfig:
    """测试工具注入配置"""

    def test_default_tool_interval_is_5(self):
        """测试：默认 tool_interval 应为 5"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.tool_agent = None
        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"
        agent_b.tool_agent = None

        # Act
        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=False
        )

        # Assert
        assert manager.tool_interval == 5

    def test_custom_tool_interval(self):
        """测试：自定义 tool_interval"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.tool_agent = None
        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"
        agent_b.tool_agent = None

        # Act
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_tools=False,
            tool_interval=10,
        )

        # Assert
        assert manager.tool_interval == 10

    def test_tool_interval_zero_disables_auto_call(self):
        """测试：tool_interval=0 禁用自动调用"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.tool_agent = None
        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"
        agent_b.tool_agent = None

        # Act
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_tools=True,
            tool_interval=0,
        )

        # Assert
        assert manager.tool_interval == 0


class TestToolInjectionInTurn:
    """测试 _turn 方法中的工具注入逻辑"""

    @pytest.mark.asyncio
    async def test_tool_not_called_on_turn_zero(self):
        """测试：第 0 轮不调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)
        agent_a.tool_agent.analyze_codebase = AsyncMock()

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )

        # Act
        await manager._turn()

        # Assert
        agent_a.tool_agent.analyze_codebase.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tool_not_called_when_interval_not_reached(self):
        """测试：未达到间隔时不调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)
        agent_a.tool_agent.analyze_codebase = AsyncMock()

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 3  # 第 3 轮，未达到 5

        # Act
        await manager._turn()

        # Assert
        agent_a.tool_agent.analyze_codebase.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tool_called_when_interval_reached(self):
        """测试：达到间隔时调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)

        # Mock 工具返回结果
        mock_tool_result = {
            "success": True,
            "summary": "代码库分析结果",
            "structure": "",
            "error": None,
        }
        agent_a.tool_agent.analyze_codebase = AsyncMock(return_value=mock_tool_result)

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5  # 第 5 轮，达到间隔

        # Act
        await manager._turn()

        # Assert
        agent_a.tool_agent.analyze_codebase.assert_awaited_once_with(".")

    @pytest.mark.asyncio
    async def test_tool_result_injected_to_messages(self):
        """测试：工具结果注入到 messages"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)

        mock_tool_result = {
            "success": True,
            "summary": "代码库分析结果",
            "structure": "",
            "error": None,
        }
        agent_a.tool_agent.analyze_codebase = AsyncMock(return_value=mock_tool_result)

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5
        initial_message_count = len(manager.messages)

        # Act
        await manager._turn()

        # Assert
        assert len(manager.messages) == initial_message_count + 1
        # 检查最后一条消息是工具结果
        last_message = manager.messages[-1]
        assert last_message["role"] == "user"
        assert "上下文更新" in last_message["content"]
        assert "代码库分析结果" in last_message["content"]

    @pytest.mark.asyncio
    async def test_tool_result_saved_to_memory(self):
        """测试：工具结果保存到 memory"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)

        mock_tool_result = {
            "success": True,
            "summary": "代码库分析结果",
            "structure": "",
            "error": None,
        }
        agent_a.tool_agent.analyze_codebase = AsyncMock(return_value=mock_tool_result)

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5

        # Mock memory.add_message
        manager.memory.add_message = MagicMock()

        # Act
        await manager._turn()

        # Assert
        manager.memory.add_message.assert_called()
        call_args = manager.memory.add_message.call_args
        assert call_args[0][0] == "user"
        assert "上下文更新" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_tool_not_called_when_disabled(self):
        """测试：enable_tools=False 时不调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = None  # 没有工具

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=False, tool_interval=5
        )
        manager.turn = 5

        # Act
        await manager._turn()

        # Assert - 不应该抛出错误，正常运行
        agent_a.respond.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_tool_failure_does_not_inject_empty_message(self):
        """测试：工具调用失败时不注入空消息"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        agent_a.tool_agent = MagicMock(spec=ToolAgent)

        # Mock 工具调用失败
        mock_tool_result = {
            "success": False,
            "summary": "",
            "structure": "",
            "error": "CLI error",
        }
        agent_a.tool_agent.analyze_codebase = AsyncMock(return_value=mock_tool_result)

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5
        initial_message_count = len(manager.messages)

        # Act
        await manager._turn()

        # Assert - 消息数不应增加
        assert len(manager.messages) == initial_message_count
