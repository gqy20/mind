"""
Unit tests for Conversation Ending Detection

测试对话结束检测功能：
- 结束标记解析
- 语义模式匹配
- 结束提议触发
- 用户确认机制
"""

import pytest
from mind.conversation_ending import (
    ConversationEndConfig,
    ConversationEndDetector,
    EndProposal,
)


class TestConversationEndConfig:
    """测试对话结束配置类"""

    def test_default_config(self):
        """测试：默认配置值"""
        # Arrange & Act
        config = ConversationEndConfig()

        # Assert
        assert config.enable_detection is True
        assert config.end_marker == "<!-- END -->"
        assert config.require_confirmation is True
        assert config.confidence_threshold == 0.7

    def test_custom_end_marker(self):
        """测试：自定义结束标记"""
        # Arrange & Act
        config = ConversationEndConfig(end_marker="::END::")

        # Assert
        assert config.end_marker == "::END::"

    def test_disabled_detection(self):
        """测试：禁用检测"""
        # Arrange & Act
        config = ConversationEndConfig(enable_detection=False)

        # Assert
        assert config.enable_detection is False


class TestConversationEndDetector:
    """测试对话结束检测器"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return ConversationEndDetector()

    def test_detect_explicit_end_marker(self, detector):
        """测试：检测明确的结束标记"""
        # Arrange
        response = """这是一个很好的观点。

综上所述，我们已经充分讨论了这个问题。
<!-- END -->"""

        # Act
        result = detector.detect_end_signal(response)

        # Assert
        assert result.should_end is True
        assert result.method == "marker"
        assert result.confidence >= 0.9

    def test_no_end_signal_in_normal_response(self, detector):
        """测试：正常响应中无结束信号"""
        # Arrange
        response = """我同意你的看法。

这个观点很有启发性，值得进一步探讨。"""

        # Act
        result = detector.detect_end_signal(response)

        # Assert
        assert result.should_end is False
        assert result.method is None
        assert result.confidence < 0.5

    def test_detect_semantic_end_patterns(self, detector):
        """测试：检测语义结束模式"""
        # Arrange
        response = "经过深入讨论，我们可以到此为止了。"

        # Act
        result = detector.detect_end_signal(response)

        # Assert
        assert result.should_end is True
        assert result.method == "semantic"
        assert "到此为止" in result.reason

    def test_multiple_patterns_increase_confidence(self, detector):
        """测试：多个模式同时出现提高置信度"""
        # Arrange
        response = """我们可以总结一下观点。
我们的对话已经达成共识，可以到此为止。"""

        # Act
        result = detector.detect_end_signal(response)

        # Assert
        assert result.should_end is True
        assert result.confidence >= 0.8
        assert "总结" in result.reason or "共识" in result.reason

    def test_chinese_end_patterns(self, detector):
        """测试：中文结束模式"""
        # Arrange
        test_cases = [
            "可以结束了",
            "我们已经充分交换了观点",
            "没有更多需要补充的了",
            "对话建议到此结束",
            "让我们总结一下",
        ]

        for response in test_cases:
            # Act
            result = detector.detect_end_signal(response)

            # Assert
            assert result.should_end is True, f"应检测到结束信号: {response}"

    def test_false_positive_prevention(self, detector):
        """测试：防止误判（假阳性）"""
        # Arrange
        # 这些看起来像结束但实际上不是的语句
        ambiguous_responses = [
            "到此为止，让我们开始下一个话题",  # 有后续
            "可以总结一下，但我还有一点补充",  # 明确说有补充
            "我们已经达成共识，继续深入探讨",  # 明确说继续
        ]

        for response in ambiguous_responses:
            # Act
            result = detector.detect_end_signal(response)

            # Assert - 这些不应该触发结束（或置信度很低）
            if "继续" in response or "补充" in response or "下一个话题" in response:
                assert result.confidence < 0.6, f"不应高置信度结束: {response}"


class TestEndProposal:
    """测试结束提议"""

    def test_create_end_proposal(self):
        """测试：创建结束提议"""
        # Arrange
        agent_name = "支持者"
        reason = "已达成共识，无明显分歧"
        confidence = 0.85

        # Act
        proposal = EndProposal(
            agent_name=agent_name,
            reason=reason,
            confidence=confidence,
        )

        # Assert
        assert proposal.agent_name == agent_name
        assert proposal.reason == reason
        assert proposal.confidence == confidence
        assert proposal.accepted is None  # 尚未确认

    def test_proposal_confirmation(self):
        """测试：提议确认机制"""
        # Arrange
        proposal = EndProposal("支持者", "讨论充分", 0.9)

        # Act
        proposal.confirm(accept=True)

        # Assert
        assert proposal.accepted is True

    def test_proposal_rejection(self):
        """测试：提议拒绝机制"""
        # Arrange
        proposal = EndProposal("挑战者", "还有疑问", 0.6)

        # Act
        proposal.confirm(accept=False)

        # Assert
        assert proposal.accepted is False

    def test_proposal_string_representation(self):
        """测试：提议的字符串表示"""
        # Arrange
        proposal = EndProposal("支持者", "讨论充分", 0.9)

        # Act
        s = str(proposal)

        # Assert
        assert "支持者" in s
        assert "讨论充分" in s
        assert "0.9" in s


class TestIntegrationWithAgent:
    """测试与 Agent 的集成"""

    def test_parse_end_marker_from_response(self):
        """测试：从完整响应中解析结束标记"""
        # Arrange
        detector = ConversationEndDetector()
        full_response = """我非常赞同你的观点。

从技术角度来看，这个方案是可行的。

综上所述，<!-- END -->"""

        # Act
        result = detector.detect_end_signal(full_response)

        # Assert
        assert result.should_end is True
        assert "标记" in result.method

    def test_remove_end_marker_from_display(self):
        """测试：移除结束标记用于显示"""
        # Arrange
        detector = ConversationEndDetector()
        response_with_marker = """这是我的观点。

<!-- END -->"""

        # Act
        cleaned = detector.clean_response_for_display(response_with_marker)

        # Assert
        assert "<!-- END -->" not in cleaned
        assert "这是我的观点" in cleaned
        assert cleaned.strip().endswith("这是我的观点")  # 标记被移除

    @pytest.mark.parametrize(
        "response,expected_end",
        [
            ("继续讨论", False),
            ("让我们总结一下，可以结束了", True),
            ("我同意，到此为止", True),
            ("还有一点要补充", False),
        ],
    )
    def test_various_responses(self, detector, response, expected_end):
        """测试：各种响应的结束检测"""
        # Act
        result = detector.detect_end_signal(response)

        # Assert
        assert result.should_end == expected_end
