"""测试 InteractionHandler 用户交互处理功能

测试用户输入检测、输入模式和处理用户输入功能。
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInteractionHandler:
    """测试 InteractionHandler 类"""

    def test_interaction_handler_can_be_imported(self):
        """测试 InteractionHandler 可以导入"""
        from mind.conversation.interaction import InteractionHandler

        assert InteractionHandler is not None

    def test_is_input_ready_in_tty(self):
        """测试在 TTY 环境中检测输入就绪"""
        from mind.conversation.interaction import InteractionHandler

        # 模拟 TTY 环境且有输入可读
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("select.select", return_value=([sys.stdin], [], [])),
        ):
            assert InteractionHandler.is_input_ready() is True

    def test_is_input_ready_no_input(self):
        """测试没有输入时返回 False"""
        from mind.conversation.interaction import InteractionHandler

        # 模拟 TTY 环境但无输入
        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("select.select", return_value=([], [], [])),
        ):
            assert InteractionHandler.is_input_ready() is False

    def test_is_input_ready_non_tty(self):
        """测试非 TTY 环境返回 False"""
        from mind.conversation.interaction import InteractionHandler

        # 模拟非 TTY 环境
        with patch("sys.stdin.isatty", return_value=False):
            assert InteractionHandler.is_input_ready() is False

    @pytest.mark.asyncio
    async def test_input_mode_with_user_input(self):
        """测试输入模式获取用户输入"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.interrupt = asyncio.Event()
        manager.configure_mock(memory=MagicMock())

        handler = InteractionHandler(manager)

        # 模拟用户输入
        with patch("builtins.input", return_value="测试消息"):
            # 模拟 handle_user_input
            handler.handle_user_input = AsyncMock()

            await handler.input_mode()

            # 验证中断标志被清除
            assert not manager.interrupt.is_set()
            # 验证处理用户输入被调用
            handler.handle_user_input.assert_called_once_with("测试消息")

    @pytest.mark.asyncio
    async def test_input_mode_empty_input(self):
        """测试空输入时取消输入"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.interrupt = asyncio.Event()
        handler = InteractionHandler(manager)

        # 模拟空输入
        with patch("builtins.input", return_value=""):
            await handler.input_mode()

            # 验证中断标志被清除
            assert not manager.interrupt.is_set()

    @pytest.mark.asyncio
    async def test_wait_for_user_input_detects_input(self):
        """测试后台监听检测到用户输入"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.interrupt = asyncio.Event()
        handler = InteractionHandler(manager)

        # 模拟第一次没有输入，第二次有输入
        with patch(
            "mind.conversation.interaction.InteractionHandler.is_input_ready",
            side_effect=[False, True],
        ):
            task = asyncio.create_task(handler.wait_for_user_input())
            # 等待任务完成
            await asyncio.sleep(0.15)
            # 验证中断标志被设置
            assert manager.interrupt.is_set()
            # 清理任务
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_handle_user_input_quit_command(self):
        """测试退出命令处理"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.is_running = True
        manager.messages = []
        handler = InteractionHandler(manager)

        await handler.handle_user_input("/quit")

        # 验证停止运行
        assert manager.is_running is False

    @pytest.mark.asyncio
    async def test_handle_user_input_clear_command(self):
        """测试清空命令处理"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.is_running = True
        manager.messages = [
            {"role": "user", "content": "主题"},
            {"role": "assistant", "content": "回复1"},
        ]
        manager.memory = MagicMock()
        manager.turn = 5
        handler = InteractionHandler(manager)

        await handler.handle_user_input("/clear")

        # 验证消息被清空（只保留第一条）
        assert len(manager.messages) == 1
        # 验证轮次被重置
        assert manager.turn == 0
        # 验证记忆被重新创建（memory 是 MemoryManager 实例）
        from mind.memory import MemoryManager

        assert isinstance(manager.memory, MemoryManager)

    @pytest.mark.asyncio
    async def test_handle_user_input_normal_message(self):
        """测试正常消息处理"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.is_running = True
        manager.messages = []
        manager.memory = MagicMock()
        handler = InteractionHandler(manager)

        await handler.handle_user_input("这是正常消息")

        # 验证消息被添加
        assert len(manager.messages) == 1
        assert manager.messages[0]["content"] == "这是正常消息"
        # 验证记忆被添加
        manager.memory.add_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_user_input_cancellation(self):
        """测试后台监听任务取消"""
        from mind.conversation.interaction import InteractionHandler

        manager = MagicMock()
        manager.interrupt = asyncio.Event()
        handler = InteractionHandler(manager)

        # 模拟始终没有输入
        with patch(
            "mind.conversation.interaction.InteractionHandler.is_input_ready",
            return_value=False,
        ):
            task = asyncio.create_task(handler.wait_for_user_input())
            # 短暂等待后取消任务
            await asyncio.sleep(0.1)
            task.cancel()

            # 验证任务被正常取消
            with pytest.raises(asyncio.CancelledError):
                await task
