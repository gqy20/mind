"""测试 EndingHandler 对话结束处理功能

测试 AI 结束提议的处理和用户确认流程。
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEndingHandler:
    """测试 EndingHandler 类"""

    def test_ending_handler_can_be_imported(self):
        """测试 EndingHandler 可以导入"""
        from mind.conversation.ending import EndingHandler

        assert EndingHandler is not None

    @pytest.mark.asyncio
    async def test_handle_proposal_user_confirms(self):
        """测试用户确认结束对话"""
        from mind.conversation.ending import EndingHandler

        manager = MagicMock()
        manager.messages = []
        manager.memory = MagicMock()
        manager.end_detector = MagicMock()
        manager.end_detector.clean_response = MagicMock(return_value="清理后的响应")
        manager.is_running = True
        manager.summary = None

        # 模拟 _summarize_conversation 方法
        async def mock_summarize():
            return "对话总结内容"

        manager._summarize_conversation = mock_summarize

        handler = EndingHandler(manager)

        # 模拟用户确认（空输入）
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):  # 抑制打印输出
                await handler.handle_proposal("AgentA", "原始响应 [END]")

        # 验证消息被添加到历史
        assert len(manager.messages) == 1
        # 验证对话停止
        assert manager.is_running is False
        # 验证总结已生成
        assert manager.summary == "对话总结内容"

    @pytest.mark.asyncio
    async def test_handle_proposal_user_continues(self):
        """测试用户选择继续对话"""
        from mind.conversation.ending import EndingHandler

        manager = MagicMock()
        manager.messages = []
        manager.memory = MagicMock()
        manager.end_detector = MagicMock()
        manager.end_detector.clean_response = MagicMock(return_value="清理后的响应")
        manager.is_running = True

        handler = EndingHandler(manager)

        # 模拟用户继续（输入内容）
        with patch("builtins.input", return_value="继续讨论"):
            with patch("builtins.print"):  # 抑制打印输出
                await handler.handle_proposal("AgentA", "原始响应 [END]")

        # 验证消息被添加到历史（包括 AI 的结束提议）
        assert len(manager.messages) == 2
        # 验证对话继续运行
        assert manager.is_running is True
        # 验证第二条消息是用户输入
        assert manager.messages[1]["role"] == "user"
        assert manager.messages[1]["content"] == "继续讨论"

    @pytest.mark.asyncio
    async def test_handle_proposal_eof_error(self):
        """测试 EOFError 处理（视为确认结束）"""
        from mind.conversation.ending import EndingHandler

        manager = MagicMock()
        manager.messages = []
        manager.memory = MagicMock()
        manager.end_detector = MagicMock()
        manager.end_detector.clean_response = MagicMock(return_value="清理后的响应")
        manager.is_running = True
        manager.summary = None

        # 模拟 _summarize_conversation 方法
        async def mock_summarize():
            return "对话总结"

        manager._summarize_conversation = mock_summarize

        handler = EndingHandler(manager)

        # 模拟 EOFError（输入结束）
        with patch("builtins.input", side_effect=EOFError):
            with patch("builtins.print"):
                await handler.handle_proposal("AgentA", "响应 [END]")

        # 验证对话停止
        assert manager.is_running is False
        # 验证总结已生成
        assert manager.summary == "对话总结"

    @pytest.mark.asyncio
    async def test_handle_proposal_adds_message_to_memory(self):
        """测试结束提议被添加到记忆"""
        from mind.conversation.ending import EndingHandler

        manager = MagicMock()
        manager.messages = []
        manager.memory = MagicMock()
        manager.end_detector = MagicMock()
        manager.end_detector.clean_response = MagicMock(return_value="清理后内容")
        manager.is_running = True

        # 添加 mock _summarize_conversation
        async def mock_summarize():
            return "总结"

        manager._summarize_conversation = mock_summarize

        handler = EndingHandler(manager)

        # 模拟用户确认
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):
                await handler.handle_proposal("AgentB", "原始 [END]")

        # 验证记忆被添加
        manager.memory.add_message.assert_called()

    @pytest.mark.asyncio
    async def test_handle_proposal_clean_response_called(self):
        """测试清理响应被正确调用"""
        from mind.conversation.ending import EndingHandler

        manager = MagicMock()
        manager.messages = []
        manager.memory = MagicMock()
        manager.end_detector = MagicMock()
        manager.end_detector.clean_response = MagicMock(return_value="已清理")
        manager.is_running = True

        # 添加 mock _summarize_conversation
        async def mock_summarize():
            return "总结"

        manager._summarize_conversation = mock_summarize

        handler = EndingHandler(manager)

        # 模拟用户确认
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):
                await handler.handle_proposal("AgentA", "原始响应 [END]")

        # 验证清理响应被调用
        manager.end_detector.clean_response.assert_called_once_with("原始响应 [END]")
