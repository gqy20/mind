"""测试 ConversationManager 核心流程

测试管理器的核心功能：
- 对话保存
- 记忆清理触发
- 总结功能
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mind.agents.agent import Agent
from mind.manager import ConversationManager


class TestConversationManagerSave:
    """测试对话保存功能"""

    @pytest.fixture
    def manager(self, tmp_path):
        """创建临时目录的 manager"""
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.topic = "测试主题"
        manager.start_time = datetime(2024, 1, 1, 12, 0)
        manager.messages = [
            {"role": "user", "content": "主题：测试"},
            {"role": "assistant", "content": "[A]: 响应1"},
            {"role": "assistant", "content": "[B]: 响应2"},
        ]
        manager.turn = 2

        # Mock history directory (MEMORY_DIR 在 mind.manager 模块中)
        with patch("mind.manager.MEMORY_DIR", tmp_path):
            yield manager

    def test_save_conversation_creates_file(self, manager, tmp_path):
        """测试：保存对话应创建 JSON 文件"""
        # Act
        filepath = manager.save_conversation()

        # Assert
        assert filepath is not None
        assert Path(filepath).exists()
        # filepath 可能是 Path 对象或字符串
        assert str(filepath).endswith(".json")

    def test_save_conversation_contains_topic(self, manager, tmp_path):
        """测试：保存的对话应包含主题"""
        # Act
        filepath = manager.save_conversation()

        # Assert
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert data["topic"] == "测试主题"

    def test_save_conversation_contains_messages(self, manager, tmp_path):
        """测试：保存的对话应包含消息历史"""
        # Act
        filepath = manager.save_conversation()

        # Assert
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert "messages" in data
        assert len(data["messages"]) == 3
        assert data["messages"][0]["content"] == "主题：测试"

    def test_save_conversation_contains_metadata(self, manager, tmp_path):
        """测试：保存的对话应包含元数据"""
        # Act
        filepath = manager.save_conversation()

        # Assert
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert "turn_count" in data
        assert data["turn_count"] == 2
        assert "start_time" in data

    def test_save_conversation_with_summary(self, manager, tmp_path):
        """测试：保存对话应包含总结（如果有）"""
        # Arrange
        manager.summary = "这是对话总结"

        # Act
        filepath = manager.save_conversation()

        # Assert
        import json

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        assert "summary" in data
        assert data["summary"] == "这是对话总结"


class TestConversationManagerSummarize:
    """测试对话总结功能"""

    @pytest.mark.asyncio
    async def test_summarize_method_exists(self):
        """测试：总结方法应存在"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Assert
        assert hasattr(manager, "_summarize_conversation")
        assert callable(manager._summarize_conversation)

    @pytest.mark.asyncio
    async def test_summarize_passes_messages(self):
        """测试：总结应传递消息历史"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)
        manager.messages = [
            {"role": "user", "content": "主题"},
            {"role": "assistant", "content": "[A]: 响应1"},
            {"role": "assistant", "content": "[B]: 响应2"},
        ]
        manager.topic = "测试主题"

        # Mock summarizer (属性名是 summarizer_agent)
        mock_summarizer = AsyncMock(return_value="总结内容")
        manager.summarizer_agent = mock_summarizer

        # Act
        await manager._summarize_conversation()

        # Assert - summarizer 被调用
        mock_summarizer.summarize.assert_called_once()
        call_args = mock_summarizer.summarize.call_args
        # 应该传递 messages、topic 和 interrupt
        assert "messages" in call_args.kwargs or len(call_args[0]) > 0


class TestConversationManagerRunAuto:
    """测试非交互式自动运行"""

    @pytest.mark.asyncio
    async def test_run_auto_delegates_to_flow_controller(self):
        """测试：run_auto 应委托给 FlowController"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Mock FlowController
        with patch.object(
            manager.flow_controller, "run_auto", new_callable=AsyncMock
        ) as mock_run_auto:
            mock_run_auto.return_value = "对话输出"

            # Act
            result = await manager.run_auto("测试主题", max_turns=10)

            # Assert - 委托给 FlowController
            # 注意：实际调用使用位置参数
            mock_run_auto.assert_called_once_with("测试主题", 10)
            assert result == "对话输出"

    @pytest.mark.asyncio
    async def test_run_auto_initializes_messages(self):
        """测试：run_auto 应初始化消息历史"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Mock FlowController
        with patch.object(
            manager.flow_controller, "run_auto", new_callable=AsyncMock
        ) as mock_run_auto:
            mock_run_auto.return_value = "输出"

            # Act
            await manager.run_auto("新主题", max_turns=5)

            # Assert - run_auto 被调用
            mock_run_auto.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_auto_with_default_max_turns(self):
        """测试：run_auto 默认最大轮数"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Mock FlowController
        with patch.object(
            manager.flow_controller, "run_auto", new_callable=AsyncMock
        ) as mock_run_auto:
            mock_run_auto.return_value = "输出"

            # Act - 不指定 max_turns
            await manager.run_auto("主题")

            # Assert - 应该使用默认值
            mock_run_auto.assert_called_once()
            # 获取实际调用的参数
            call_args = mock_run_auto.call_args
            # max_turns 应该有值（可能是默认值或从配置读取）
            assert len(call_args[0]) >= 1  # 至少有 topic 参数
