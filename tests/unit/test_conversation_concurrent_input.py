"""测试并发输入监听功能

这个测试套件验证在智能体响应期间能够并发检测用户输入，
解决"智能体输出时按 Enter 被卡住"的问题。
"""

import asyncio
from unittest.mock import patch

import pytest

from mind.agent import Agent
from mind.conversation import ConversationManager


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

        # 模拟在响应过程中有用户输入
        async def simulate_input_during_respond():
            """模拟用户在智能体输出过程中按 Enter"""
            await asyncio.sleep(0.05)  # 等待一小段时间
            # 这里模拟 _is_input_ready() 返回 True
            # 但由于当前实现是串行的，这个输入不会被检测到
            return True

        with patch.object(agent_a, "respond", side_effect=slow_respond):
            # Act
            input_task = asyncio.create_task(simulate_input_during_respond())
            await manager._turn()
            has_input = await input_task

            # Assert
            # 当前实现：输入在响应期间不会被检测到
            # 预期实现：输入应该被检测到并设置 interrupt
            # 这个测试会失败，因为当前实现是串行的
            assert has_input, "应该检测到用户输入"
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

        # 模拟 _is_input_ready 返回 True
        with patch("mind.conversation._is_input_ready", return_value=True):
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
            await asyncio.sleep(0.1)  # 在响应开始后触发
            with patch("mind.conversation._is_input_ready", return_value=True):
                if hasattr(manager, "_wait_for_user_input"):
                    await manager._wait_for_user_input()

        with patch.object(agent_a, "respond", side_effect=slow_respond):
            # Act
            input_task = asyncio.create_task(trigger_input())
            await manager._turn()
            await input_task

            # Assert
            assert response_started, "响应应该已经开始"
            # 当前实现会失败：响应会完成而不被中断
            # 预期行为：响应应该被中断
            assert not response_completed, "响应应该被中断"
            assert manager.interrupt.is_set(), "中断标志应该被设置"
