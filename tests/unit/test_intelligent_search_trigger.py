"""测试智能搜索触发功能

这个测试套件验证 AI 主动请求搜索和关键词检测的智能触发机制。
"""

import pytest

from mind.agent import Agent
from mind.conversation import ConversationManager


class TestAISearchRequest:
    """测试 AI 主动请求搜索功能"""

    @pytest.mark.asyncio
    async def test_detect_search_request_in_response(self):
        """测试：检测 AI 响应中的搜索请求"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        # AI 响应包含搜索请求
        response_with_search = "我不确定最新的信息 [搜索: GPT-5 发布时间]"

        # Act
        has_request = manager._has_search_request(response_with_search)

        # Assert
        assert has_request is True

    @pytest.mark.asyncio
    async def test_extract_query_from_search_request(self):
        """测试：从搜索请求中提取关键词"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        response = "让我查一下 [搜索: 量子计算最新进展]"

        # Act
        query = manager._extract_search_from_response(response)

        # Assert
        assert query == "量子计算最新进展"

    @pytest.mark.asyncio
    async def test_no_search_request_in_normal_response(self):
        """测试：普通响应不触发搜索"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        normal_response = "我认为 AI 意识是个复杂的问题"

        # Act
        has_request = manager._has_search_request(normal_response)

        # Assert
        assert has_request is False


class TestKeywordDetection:
    """测试关键词智能检测功能"""

    @pytest.mark.asyncio
    async def test_detect_uncertainty_keywords(self):
        """测试：检测不确定性关键词触发搜索"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        manager.messages = [
            {"role": "user", "content": "GPT-5 发布了吗？"},
            {"role": "assistant", "content": "我不确定最新的发布时间"},
        ]

        # Act
        should_search = manager._should_search_by_keywords()

        # Assert
        assert should_search is True

    @pytest.mark.asyncio
    async def test_detect_factual_question_keywords(self):
        """测试：检测事实性问题关键词"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        manager.messages = [
            {"role": "user", "content": "当前的具体数据是多少？"},
        ]

        # Act
        should_search = manager._should_search_by_keywords()

        # Assert
        assert should_search is True

    @pytest.mark.asyncio
    async def test_no_trigger_in_opinion_discussion(self):
        """测试：观点讨论不触发搜索"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        manager.messages = [
            {"role": "user", "content": "你觉得 AI 有意识吗？"},
            {"role": "assistant", "content": "我认为这是一个哲学问题"},
        ]

        # Act
        should_search = manager._should_search_by_keywords()

        # Assert
        assert should_search is False


class TestIntelligentSearchTrigger:
    """测试综合智能触发逻辑"""

    @pytest.mark.asyncio
    async def test_ai_request_has_highest_priority(self):
        """测试：AI 主动请求优先级最高"""
        # Arrange
        agent_a = Agent(name="A", system_prompt="你是A")
        agent_b = Agent(name="B", system_prompt="你是B")
        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
            enable_search=True,
        )
        manager.messages = [{"role": "user", "content": "讨论 AI"}]

        ai_response = "让我查查 [搜索: AI 意识最新研究]"

        # Act - 传入 AI 响应检测搜索请求
        need_search = manager._should_trigger_search(last_response=ai_response)

        # Assert - AI 请求应该触发
        assert need_search is True

    @pytest.mark.asyncio
    async def test_keyword_trigger_when_no_ai_request(self):
        """测试：无 AI 请求时，关键词检测作为补充"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
        )

        manager.messages = [
            {"role": "user", "content": "最新的发布时间是什么？"},
        ]

        # Act
        need_search = manager._should_trigger_search()

        # Assert
        assert need_search is True

    @pytest.mark.asyncio
    async def test_fallback_to_interval_when_no_signals(self):
        """测试：无信号时，间隔作为兜底"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
            enable_search=True,
            search_interval=3,
        )
        manager.messages = [
            {"role": "user", "content": "普通观点讨论"},
        ]
        manager.turn = 3  # 达到间隔

        # Act
        need_search = manager._should_trigger_search()

        # Assert
        assert need_search is True

    @pytest.mark.asyncio
    async def test_no_trigger_when_all_conditions_false(self):
        """测试：所有条件都不满足时不触发"""
        # Arrange
        manager = ConversationManager(
            agent_a=Agent(name="A", system_prompt="你是A"),
            agent_b=Agent(name="B", system_prompt="你是B"),
            enable_search=False,  # 禁用
        )
        manager.messages = [
            {"role": "user", "content": "普通讨论"},
        ]
        manager.turn = 1  # 未达到间隔

        # Act
        need_search = manager._should_trigger_search()

        # Assert
        assert need_search is False
