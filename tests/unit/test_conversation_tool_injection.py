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

from mind.agents.agent import Agent
from mind.conversation import ConversationManager


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
        # Mock query_tool 方法
        agent_a.query_tool = AsyncMock(return_value="工具结果")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )

        # Act
        await manager._turn()

        # Assert - 第 0 轮不应该调用工具
        agent_a.query_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_not_called_when_interval_not_reached(self):
        """测试：未达到间隔时不调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        # Mock query_tool 方法
        agent_a.query_tool = AsyncMock(return_value="工具结果")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 3  # 第 3 轮，未达到 5

        # Act
        await manager._turn()

        # Assert - 未达到间隔，不应该调用工具
        agent_a.query_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_called_when_interval_reached(self):
        """测试：达到间隔时调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        # Mock query_tool 方法返回工具结果
        agent_a.query_tool = AsyncMock(return_value="代码库分析结果")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5  # 第 5 轮，达到间隔

        # Act
        await manager._turn()

        # Assert - 应该调用 query_tool，传入 messages
        agent_a.query_tool.assert_called_once()
        # 检查调用参数
        call_args = agent_a.query_tool.call_args
        assert call_args[0][0] == "总结当前对话"  # question 参数
        # messages 是第二个位置参数
        assert len(call_args[0]) == 2  # question 和 messages
        assert call_args[0][1] is not None  # messages 不为 None

    @pytest.mark.asyncio
    async def test_tool_result_injected_to_messages(self):
        """测试：工具结果注入到 messages"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        # Mock query_tool 方法返回对话摘要
        agent_a.query_tool = AsyncMock(return_value="对话摘要")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5
        initial_message_count = len(manager.messages)

        # Act
        await manager._turn()

        # Assert - 应该有 2 条新消息（工具消息 + 响应消息）
        assert len(manager.messages) == initial_message_count + 2
        # 检查倒数第二条消息是工具结果（最后一条是响应）
        tool_message = manager.messages[-2]
        assert tool_message["role"] == "user"
        assert "上下文更新" in tool_message["content"]
        assert "对话摘要" in tool_message["content"]

    @pytest.mark.asyncio
    async def test_tool_result_saved_to_memory(self):
        """测试：工具结果保存到 memory"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        # Mock query_tool 方法返回对话摘要
        agent_a.query_tool = AsyncMock(return_value="对话摘要")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5

        # Mock memory.add_message 以跟踪调用
        add_message_calls = []

        def track_add_message(role, content):
            add_message_calls.append((role, content))

        manager.memory.add_message = track_add_message

        # Act
        await manager._turn()

        # Assert - 应该调用 add_message，最后一次是工具消息
        assert len(add_message_calls) >= 1
        tool_msg_call = [c for c in add_message_calls if "上下文更新" in c[1]][0]
        assert tool_msg_call[0] == "user"

    @pytest.mark.asyncio
    async def test_tool_not_called_when_disabled(self):
        """测试：enable_tools=False 时不调用工具"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=False, tool_interval=5
        )
        manager.turn = 5

        # Act
        await manager._turn()

        # Assert - 不应该抛出错误，正常运行
        agent_a.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_failure_does_not_inject_empty_message(self):
        """测试：工具调用失败时不注入空消息"""
        # Arrange
        agent_a = MagicMock(spec=Agent)
        agent_a.name = "AgentA"
        agent_a.respond = AsyncMock(return_value="响应")
        # Mock query_tool 方法返回 None（表示失败）
        agent_a.query_tool = AsyncMock(return_value=None)

        agent_b = MagicMock(spec=Agent)
        agent_b.name = "AgentB"

        manager = ConversationManager(
            agent_a=agent_a, agent_b=agent_b, enable_tools=True, tool_interval=5
        )
        manager.turn = 5
        initial_message_count = len(manager.messages)

        # Act
        await manager._turn()

        # Assert - 应该只有响应消息，没有工具消息
        assert len(manager.messages) == initial_message_count + 1
        # 最后一条应该是响应（assistant role）
        assert manager.messages[-1]["role"] == "assistant"
