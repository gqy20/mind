"""测试对话系统与网络搜索的集成

这个测试套件验证对话系统能够在适当时候触发网络搜索。
"""

from unittest.mock import patch

import pytest

from mind.agent import Agent
from mind.conversation import ConversationManager


class TestConversationSearchIntegration:
    """测试对话中的网络搜索集成"""

    @pytest.mark.asyncio
    async def test_search_enabled_with_flag(self):
        """测试：设置 enable_search 应该启用网络搜索"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,  # 启用搜索
        )

        # Assert
        assert manager.enable_search is True

    @pytest.mark.asyncio
    async def test_search_disabled_by_default(self):
        """测试：默认情况下网络搜索应该禁用"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(agent_a=agent_a, agent_b=agent_b)

        # Assert
        assert manager.enable_search is False

    @pytest.mark.asyncio
    async def test_search_called_during_turn(self):
        """测试：在特定轮次应该调用网络搜索"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,
            search_interval=2,  # 每 2 轮搜索一次
        )
        manager.messages.append({"role": "user", "content": "讨论 AI 意识"})

        # Mock 响应和搜索
        with patch.object(agent_a, "respond", return_value="[A]: AI 可能没有意识"):
            with patch("mind.tools.search_tool.search_web") as mock_search:
                mock_search.return_value = "**网络搜索结果**: AI 意识\n1. 一些结果"

                # 设置为第 2 轮
                manager.turn = 2

                # Act
                await manager._turn()

                # Assert
                mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_result_injected_to_messages(self):
        """测试：搜索结果应该注入到对话历史"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,
            search_interval=2,
        )
        manager.messages.append({"role": "user", "content": "讨论 AI"})

        initial_count = len(manager.messages)

        search_result = "**网络搜索结果**: AI\n1. 测试结果"

        with patch.object(agent_a, "respond", return_value="[A]: 回复"):
            with patch("mind.tools.search_tool.search_web", return_value=search_result):
                manager.turn = 2

                # Act
                await manager._turn()

                # Assert
                # 应该添加搜索结果消息
                assert len(manager.messages) > initial_count
                # 搜索结果应该在倒数第二条（最后是智能体响应）
                search_msg = manager.messages[-2]
                assert search_msg["role"] == "user"
                assert "网络搜索" in search_msg["content"]

    @pytest.mark.asyncio
    async def test_search_not_called_when_disabled(self):
        """测试：禁用时不应调用网络搜索"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=False,  # 禁用搜索
        )
        manager.messages.append({"role": "user", "content": "讨论 AI"})

        with patch.object(agent_a, "respond", return_value="[A]: 回复"):
            with patch("mind.tools.search_tool.search_web") as mock_search:
                manager.turn = 2

                # Act
                await manager._turn()

                # Assert
                mock_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_topic_extracted_from_context(self):
        """测试：应该从对话上下文中提取搜索关键词"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,
            search_interval=2,
        )
        # 模拟对话历史
        manager.messages = [
            {"role": "user", "content": "量子计算是什么？"},
            {"role": "assistant", "content": "[A]: 量子计算使用量子比特"},
        ]

        with patch.object(agent_a, "respond", return_value="[A]: 继续"):
            with patch("mind.tools.search_tool.search_web") as mock_search:
                mock_search.return_value = "搜索结果"
                manager.turn = 2

                # Act
                await manager._turn()

                # Assert
                # 搜索关键词应该与对话主题相关
                call_args = mock_search.call_args
                query = call_args[0][0] if call_args[0] else call_args[1].get("query")
                # 关键词应该包含对话中的概念
                assert query is not None
                assert len(query) > 0
