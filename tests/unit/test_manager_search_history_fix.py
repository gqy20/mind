"""测试 ConversationManager 正确传递 search_history 到 ResponseHandler

问题：ConversationManager.__post_init__ 只设置了 agent.search_history，
但没有设置 agent.response_handler.search_history，导致搜索结果无法保存。
"""

from unittest.mock import patch

import pytest

from mind.agents.agent import Agent
from mind.config import AgentConfig, SettingsConfig
from mind.manager import ConversationManager


@pytest.fixture
def mock_agent_config():
    """创建模拟的智能体配置"""
    return AgentConfig(
        name="测试智能体",
        system_prompt="你是一个测试智能体。",
        model="claude-3-5-sonnet-20241022",
    )


@pytest.fixture
def mock_settings():
    """创建模拟的设置配置"""
    return SettingsConfig()


@pytest.fixture
def agent_a(mock_agent_config):
    """创建智能体 A"""
    with patch("mind.agents.agent.AnthropicClient"):
        agent = Agent(
            name="支持者",
            system_prompt="你是支持者。",
            model="claude-3-5-sonnet-20241022",
        )
    return agent


@pytest.fixture
def agent_b(mock_agent_config):
    """创建智能体 B"""
    with patch("mind.agents.agent.AnthropicClient"):
        agent = Agent(
            name="挑战者",
            system_prompt="你是挑战者。",
            model="claude-3-5-sonnet-20241022",
        )
    return agent


@pytest.fixture
def conversation_manager(agent_a, agent_b):
    """创建对话管理器（启用搜索）"""
    with (
        patch("mind.agents.summarizer.SummarizerAgent"),
        patch("mind.conversation.ending_detector.ConversationEndDetector"),
    ):
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,
            search_interval=5,
        )
    return manager


class TestSearchHistoryPropagation:
    """测试 search_history 正确传递到 ResponseHandler"""

    def test_search_history_propagated_to_response_handler(self, conversation_manager):
        """测试 search_history 被正确传递到 response_handler

        Given: ConversationManager 启用搜索功能
        When: ConversationManager 初始化完成
        Then: 两个智能体的 response_handler.search_history 应该被设置
        """
        # Arrange & Act
        # conversation_manager 已经在 fixture 中初始化

        # Assert
        assert conversation_manager.search_history is not None, (
            "ConversationManager.search_history 应该被初始化"
        )

        assert (
            conversation_manager.agent_a.response_handler.search_history is not None
        ), "agent_a.response_handler.search_history 应该被设置"

        assert (
            conversation_manager.agent_b.response_handler.search_history is not None
        ), "agent_b.response_handler.search_history 应该被设置"

        # 验证两个智能体使用同一个 SearchHistory 实例
        assert (
            conversation_manager.agent_a.response_handler.search_history
            is conversation_manager.search_history
        ), "agent_a.response_handler.search_history 应该指向同一个实例"

        assert (
            conversation_manager.agent_b.response_handler.search_history
            is conversation_manager.search_history
        ), "agent_b.response_handler.search_history 应该指向同一个实例"

    def test_search_history_same_instance_for_both_agents(self, conversation_manager):
        """测试两个智能体共享同一个 SearchHistory 实例

        Given: ConversationManager 启用搜索功能
        When: ConversationManager 初始化完成
        Then: 两个智能体应该共享同一个 SearchHistory 实例
        """
        # Arrange & Act
        # conversation_manager 已经在 fixture 中初始化

        # Assert
        agent_a_history = conversation_manager.agent_a.response_handler.search_history
        agent_b_history = conversation_manager.agent_b.response_handler.search_history

        assert agent_a_history is agent_b_history, (
            "两个智能体应该共享同一个 SearchHistory 实例"
        )

    def test_search_history_file_created(self, conversation_manager):
        """测试搜索历史文件被正确创建

        Given: ConversationManager 启用搜索功能
        When: ConversationManager 初始化完成
        Then: 搜索历史文件应该存在且为空数组
        """
        # Arrange & Act
        # conversation_manager 已经在 fixture 中初始化

        # Assert
        search_history = conversation_manager.search_history
        assert search_history.file_path.exists(), (
            f"搜索历史文件应该存在: {search_history.file_path}"
        )

        # 验证文件内容是空的搜索列表
        import json

        content = json.loads(search_history.file_path.read_text(encoding="utf-8"))
        assert content == {"searches": []}, "搜索历史文件应该包含空的 searches 数组"


class TestSearchHistoryDisabled:
    """测试禁用搜索时 search_history 的行为"""

    @pytest.fixture
    def manager_no_search(self, agent_a, agent_b):
        """创建禁用搜索的对话管理器"""
        with (
            patch("mind.agents.summarizer.SummarizerAgent"),
            patch("mind.conversation.ending_detector.ConversationEndDetector"),
        ):
            manager = ConversationManager(
                agent_a=agent_a,
                agent_b=agent_b,
                enable_search=False,
            )
        return manager

    def test_search_history_not_initialized_when_disabled(self, manager_no_search):
        """测试禁用搜索时 search_history 不被初始化

        Given: ConversationManager 禁用搜索功能
        When: ConversationManager 初始化完成
        Then: search_history 应该为 None
        """
        # Arrange & Act
        # manager_no_search 已经在 fixture 中初始化

        # Assert
        assert manager_no_search.search_history is None, (
            "禁用搜索时 search_history 应该为 None"
        )

        assert manager_no_search.agent_a.response_handler.search_history is None, (
            "agent_a.response_handler.search_history 应该为 None"
        )

        assert manager_no_search.agent_b.response_handler.search_history is None, (
            "agent_b.response_handler.search_history 应该为 None"
        )
