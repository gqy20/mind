"""测试 AI 分析功能

测试真正的 AI 分析来判断对话是否应该结束，包括评分机制。
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class AnalysisResult:
    """AI 分析结果"""

    should_end: bool
    score: int
    threshold: int
    reason: str
    loop_score: int
    consensus_score: int
    expression_score: int


class TestAIAnalysis:
    """测试 AI 分析功能"""

    def test_ai_analysis_result_can_be_imported(self):
        """测试 AnalysisResult 可以被导入"""
        from mind.conversation.ending_detector import AnalysisResult

        assert AnalysisResult is not None

    @pytest.mark.asyncio
    async def test_ai_analysis_with_high_score_triggers_end(self):
        """测试高分（≥80）触发对话结束"""
        from mind.conversation.ending_detector import (
            ConversationEndConfig,
            ConversationEndDetector,
        )

        config = ConversationEndConfig(
            enable_analysis_detection=True,
            analysis_end_threshold=80,
            analysis_min_turns=10,
        )
        detector = ConversationEndDetector(config)

        # 模拟 AI 返回高分分析
        mock_analysis = AnalysisResult(
            should_end=True,
            score=85,
            threshold=80,
            reason="对话已充分展开，双方观点已表达完整",
            loop_score=25,
            consensus_score=35,
            expression_score=25,
        )

        # 模拟 _analyze_by_ai 方法
        async def mock_analyze(messages, current_turn):
            return mock_analysis

        detector._analyze_by_ai = mock_analyze

        # 准备测试消息（模拟 10 轮对话）
        messages = [{"role": "user", "content": f"轮次 {i}"} for i in range(1, 12)]

        # 测试检测
        result = detector.detect(
            response="<!-- END -->", current_turn=11, messages=messages
        )

        # 验证：高分应该触发结束，且包含过渡轮数
        assert result.detected is True
        assert result.transition == 2  # 默认过渡轮数
        assert "分析" in result.method or "verified" in result.method

    @pytest.mark.asyncio
    async def test_ai_analysis_with_low_score_does_not_trigger_end(self):
        """测试低分（<80）不触发对话结束"""
        from mind.conversation.ending_detector import (
            ConversationEndConfig,
            ConversationEndDetector,
        )

        config = ConversationEndConfig(
            enable_analysis_detection=True,
            analysis_end_threshold=80,
            analysis_min_turns=10,
        )
        detector = ConversationEndDetector(config)

        # 模拟 AI 返回低分分析
        mock_analysis = AnalysisResult(
            should_end=False,
            score=65,
            threshold=80,
            reason="对话仍在进行中，观点尚未充分表达",
            loop_score=10,
            consensus_score=20,
            expression_score=35,
        )

        async def mock_analyze(messages, current_turn):
            return mock_analysis

        detector._analyze_by_ai = mock_analyze

        # 准备测试消息
        messages = [{"role": "user", "content": f"轮次 {i}"} for i in range(1, 12)]

        # 测试检测
        result = detector.detect(
            response="<!-- END -->", current_turn=11, messages=messages
        )

        # 验证：低分不应该触发结束
        assert result.detected is False

    @pytest.mark.asyncio
    async def test_ai_analysis_includes_scoring_details(self):
        """测试 AI 分析包含详细的评分维度"""
        from mind.conversation.ending_detector import (
            ConversationEndConfig,
            ConversationEndDetector,
        )

        config = ConversationEndConfig(
            enable_analysis_detection=True, analysis_min_turns=5
        )
        detector = ConversationEndDetector(config)

        # 模拟完整的评分分析
        mock_analysis = AnalysisResult(
            should_end=True,
            score=90,
            threshold=80,
            reason="对话达成明确共识，观点充分表达",
            loop_score=28,  # 高循环分数
            consensus_score=38,  # 高共识分数
            expression_score=24,  # 中等表达分数
        )

        async def mock_analyze(messages, current_turn):
            return mock_analysis

        detector._analyze_by_ai = mock_analyze

        messages = [{"role": "user", "content": "测试"} for _ in range(10)]

        result = detector.detect(
            response="<!-- END -->", current_turn=10, messages=messages
        )

        # 验证分析结果包含评分
        assert result.detected is True
        assert result.reason == "对话达成明确共识，观点充分表达"

    @pytest.mark.asyncio
    async def test_ai_analysis_with_conversable_client(self):
        """测试使用真实的 ConversableClient 进行 AI 分析"""
        from mind.conversation.ending_detector import (
            ConversationEndConfig,
            ConversationEndDetector,
        )

        config = ConversationEndConfig(
            enable_analysis_detection=True,
            analysis_min_turns=3,
            analysis_end_threshold=70,
        )

        # Mock AnthropicClient
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value="分析结果：对话已达成共识")

        detector = ConversationEndDetector(config)
        detector._client = mock_client

        messages = [
            {"role": "assistant", "content": "我同意你的观点"},
            {"role": "assistant", "content": "我也同意"},
            {"role": "assistant", "content": "达成共识"},
        ]

        # 这个测试会失败，因为 _analyze_by_ai 方法还不存在
        with pytest.raises(AttributeError):
            await detector._analyze_by_ai(messages, current_turn=3)
