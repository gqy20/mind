"""测试并发输入监听功能

这个测试套件验证在智能体响应期间能够并发检测用户输入，
解决"智能体输出时按 Enter 被卡住"的问题。
"""

import asyncio
from unittest.mock import patch

import pytest

from mind.agents.agent import Agent
from mind.manager import ConversationManager


class TestConcurrentInputMonitoring:
    """测试并发输入监听功能"""

    @pytest.mark.asyncio
    async def test_input_during_respond_should_interrupt(self):
        """测试：智能体响应期间按 Enter 应该能够中断"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "开始"})

        # 模拟一个长时间的响应
        async def slow_respond(messages, interrupt):
            """模拟智能体正在输出，需要一些时间"""
            await asyncio.sleep(0.2)  # 模拟网络延迟
            # 在这个延迟期间，主循环应该能检测到用户输入
            if interrupt.is_set():
                return None
            return "A的回复"

        # 使用一个可控制的函数来模拟 is_input_ready
        input_ready = False

        def mock_is_input_ready():
            return input_ready

        # 模拟在响应过程中有用户输入
        async def simulate_input_during_respond():
            """模拟用户在智能体输出过程中按 Enter"""
            nonlocal input_ready
            await asyncio.sleep(0.05)  # 等待一小段时间
            input_ready = True  # 设置输入就绪标志
            await asyncio.sleep(0.15)  # 等待后台任务检测到输入

        with patch.object(agent_a, "respond", side_effect=slow_respond):
            # 更新 patch 路径到 FlowController
            with patch(
                "mind.conversation.flow.InteractionHandler.is_input_ready",
                side_effect=mock_is_input_ready,
            ):
                # Act
                input_task = asyncio.create_task(simulate_input_during_respond())
                await manager._turn()
                await input_task

                # Assert
                # 预期实现：输入应该被检测到并设置 interrupt
                assert manager.interrupt.is_set(), "中断标志应该被设置"

    @pytest.mark.asyncio
    async def test_turn_should_monitor_input_concurrently(self):
        """测试：_turn 方法应该并发监听输入"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "开始"})

        # 检查是否有并发监听输入的方法
        # Act
        has_concurrent_monitor = hasattr(manager, "_wait_for_user_input")

        # Assert
        assert has_concurrent_monitor, (
            "ConversationManager 应该有 _wait_for_user_input 方法"
        )

    @pytest.mark.asyncio
    async def test_wait_for_user_input_sets_interrupt(self):
        """测试：_wait_for_user_input 方法应该在检测到输入时设置 interrupt"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # 模拟 is_input_ready 返回 True
        with patch(
            "mind.conversation.interaction.InteractionHandler.is_input_ready",
            return_value=True,
        ):
            # Act
            if hasattr(manager, "_wait_for_user_input"):
                await manager._wait_for_user_input()

            # Assert
            assert manager.interrupt.is_set(), "检测到输入时应该设置中断标志"


class TestConcurrentInputIntegration:
    """集成测试：验证完整的并发输入流程"""

    @pytest.mark.asyncio
    async def test_concurrent_input_flow(self):
        """测试：完整的并发输入流程"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages.append({"role": "user", "content": "开始"})

        # 创建一个慢响应模拟
        response_started = False
        response_completed = False
        input_ready = False

        def mock_is_input_ready():
            return input_ready

        async def slow_respond(messages, interrupt):
            nonlocal response_started, response_completed
            response_started = True
            await asyncio.sleep(0.3)
            if interrupt.is_set():
                return None
            response_completed = True
            return "A的回复"

        # 模拟输入到达
        async def trigger_input():
            nonlocal input_ready
            await asyncio.sleep(0.1)  # 在响应开始后触发
            input_ready = True
            await asyncio.sleep(0.2)  # 等待后台任务检测

        with patch.object(agent_a, "respond", side_effect=slow_respond):
            # 更新 patch 路径到 FlowController
            with patch(
                "mind.conversation.flow.InteractionHandler.is_input_ready",
                side_effect=mock_is_input_ready,
            ):
                # Act
                input_task = asyncio.create_task(trigger_input())
                await manager._turn()
                await input_task

                # Assert
                assert response_started, "响应应该已经开始"
                # 预期行为：响应应该被中断
                assert not response_completed, "响应应该被中断"
                assert manager.interrupt.is_set(), "中断标志应该被设置"
