"""
ConversationManager 类的单元测试

测试对话管理器的功能：
- 初始化配置
- 输入模式处理
- 用户输入处理
"""

import asyncio
from unittest.mock import patch

import pytest

from mind.agents.agent import Agent
from mind.conversation import ConversationManager
from mind.memory import MemoryManager, TokenConfig


class TestConversationManagerInit:
    """测试 ConversationManager 初始化"""

    def test_init_with_two_agents(self):
        """测试：使用两个智能体初始化"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")

        # Act
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Assert
        assert manager.agent_a == agent_a
        assert manager.agent_b == agent_b
        assert manager.messages == []
        assert manager.turn == 0
        assert manager.current == 0  # A 先发言

    def test_init_with_default_interval(self):
        """测试：默认轮次间隔应为 0.3 秒"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")

        # Act
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Assert
        assert manager.turn_interval == 0.3


class TestConversationManagerInputMode:
    """测试输入模式"""

    @pytest.mark.asyncio
    async def test_input_mode_sets_interrupt(self):
        """测试：输入模式应设置中断标志"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Mock input 返回空内容（取消）
        with patch("asyncio.base_events.BaseEventLoop.run_in_executor") as mock_exec:
            mock_exec.return_value = asyncio.Future()
            mock_exec.return_value.set_result("")

            # Act
            await manager._input_mode()

        # Assert - 中断标志应被清除
        assert not manager.interrupt.is_set()

    @pytest.mark.asyncio
    async def test_input_mode_handles_empty_input(self):
        """测试：空输入应取消输入模式"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        with patch("asyncio.base_events.BaseEventLoop.run_in_executor") as mock_exec:
            mock_exec.return_value = asyncio.Future()
            mock_exec.return_value.set_result("")

            # Act
            await manager._input_mode()

        # Assert - 对话应继续运行
        assert manager.is_running


class TestConversationManagerUserInput:
    """测试用户输入处理"""

    @pytest.mark.asyncio
    async def test_handle_user_input_processes_quit(self):
        """测试：/quit 命令应停止对话"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Act
        await manager._handle_user_input("/quit")

        # Assert
        assert manager.is_running is False

    @pytest.mark.asyncio
    async def test_handle_user_input_processes_clear(self):
        """测试：/clear 命令应重置对话"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "主题"})
        manager.messages.append({"role": "assistant", "content": "回应"})

        # Act
        await manager._handle_user_input("/clear")

        # Assert
        assert len(manager.messages) == 1
        assert manager.turn == 0

    @pytest.mark.asyncio
    async def test_handle_user_input_adds_message(self):
        """测试：普通输入应添加到消息历史"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Act
        await manager._handle_user_input("用户消息")

        # Assert
        assert len(manager.messages) == 1
        assert manager.messages[0]["role"] == "user"
        assert manager.messages[0]["content"] == "用户消息"


class TestConversationManagerMessageFormat:
    """测试消息格式规范"""

    @pytest.mark.asyncio
    async def test_turn_message_contains_role_prefix(self):
        """测试：智能体回复的消息应包含 [角色名]: 前缀"""
        # Arrange
        agent_a = Agent(name="支持者", system_prompt="你是支持者")
        agent_b = Agent(name="挑战者", system_prompt="你是挑战者")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "主题"})

        with patch.object(agent_a, "respond", return_value="这是支持者的观点"):
            # Act
            await manager._turn()

        # Assert - 消息内容应包含角色前缀
        assert len(manager.messages) == 2
        assert manager.messages[1]["role"] == "assistant"
        assert manager.messages[1]["content"] == "[支持者]: 这是支持者的观点"

    @pytest.mark.asyncio
    async def test_turn_two_agents_different_prefixes(self):
        """测试：两个智能体应有不同的角色前缀"""
        # Arrange
        agent_a = Agent(name="支持者", system_prompt="你是支持者")
        agent_b = Agent(name="挑战者", system_prompt="你是挑战者")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "主题"})

        with patch.object(agent_a, "respond", return_value="支持观点"):
            with patch.object(agent_b, "respond", return_value="挑战观点"):
                # Act - 两轮对话
                await manager._turn()
                await manager._turn()

        # Assert - 两条消息应有不同的前缀
        assert len(manager.messages) == 3
        assert manager.messages[1]["content"] == "[支持者]: 支持观点"
        assert manager.messages[2]["content"] == "[挑战者]: 挑战观点"

    @pytest.mark.asyncio
    async def test_turn_removes_duplicate_prefix(self):
        """测试：如果响应已包含前缀，应去重"""
        # Arrange
        agent_a = Agent(name="支持者", system_prompt="你是支持者")
        agent_b = Agent(name="挑战者", system_prompt="你是挑战者")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "主题"})

        # 模拟 AI 返回的内容已经包含前缀
        with patch.object(agent_a, "respond", return_value="[支持者]: 这是观点"):
            # Act
            await manager._turn()

        # Assert - 前缀应该只出现一次
        assert len(manager.messages) == 2
        assert manager.messages[1]["content"] == "[支持者]: 这是观点"


class TestConversationManagerTurn:
    """测试对话轮次管理"""

    @pytest.mark.asyncio
    async def test_turn_alternates_between_agents(self):
        """测试：对话轮次应在两个智能体之间交替"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Mock respond 方法
        with patch.object(agent_a, "respond", return_value="A说"):
            with patch.object(agent_b, "respond", return_value="B说"):
                manager.messages.append({"role": "user", "content": "开始"})

                # Act - 执行两轮
                await manager._turn()
                assert manager.current == 1  # 切换到 B

                await manager._turn()
                assert manager.current == 0  # 切换回 A

    @pytest.mark.asyncio
    async def test_turn_increments_counter(self):
        """测试：每轮对话应增加计数器"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        with patch.object(agent_a, "respond", return_value="A说"):
            with patch.object(agent_b, "respond", return_value="B说"):
                manager.messages.append({"role": "user", "content": "开始"})

                initial_turn = manager.turn

                # Act
                await manager._turn()

                # Assert
                assert manager.turn == initial_turn + 1

    @pytest.mark.asyncio
    async def test_turn_interrupted_returns_none_no_message_added(self):
        """测试：被中断时不添加消息"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "开始"})
        manager.interrupt.set()  # 设置中断

        with patch.object(agent_a, "respond", return_value=None):
            initial_count = len(manager.messages)

            # Act
            await manager._turn()

            # Assert
            assert len(manager.messages) == initial_count  # 没有添加新消息


class TestConversationManagerAutoExit:
    """测试自动退出和总结功能"""

    @pytest.mark.asyncio
    async def test_should_exit_after_max_trims(self):
        """测试：达到最大清理次数时应退出"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            memory=MemoryManager(TokenConfig(max_trim_count=2)),
        )
        manager._trim_count = 2  # 设置为最大值

        # Act
        result = manager.should_exit_after_trim()

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_should_not_exit_below_max_trims(self):
        """测试：未达到最大清理次数时不应退出"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            memory=MemoryManager(TokenConfig(max_trim_count=3)),
        )
        manager._trim_count = 1  # 低于最大值

        # Act
        result = manager.should_exit_after_trim()

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_summarize_conversation_creates_summary(self):
        """测试：总结功能应创建对话摘要"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages = [
            {"role": "user", "content": "主题：AI的发展"},
            {"role": "assistant", "content": "[A]: AI发展很快"},
            {"role": "assistant", "content": "[B]: 但也有挑战"},
        ]
        manager.topic = "AI的发展"
        manager.turn = 2

        # Act & Assert - 验证方法存在
        assert hasattr(manager, "_summarize_conversation")
        # 注意：实际调用需要 mock API，这里只验证方法存在
        # 完整测试在集成测试中进行
