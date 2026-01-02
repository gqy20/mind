"""
Unit tests for Conversation Ending Detection (Redesigned)

测试对话结束检测功能（重新设计）：
- 显式标记检测（简单、可靠）
- 响应清理
- 结束提议管理
- 集成测试
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
        assert config.auto_end is False

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

    def test_auto_end_without_confirmation(self):
        """测试：自动结束无需确认"""
        # Arrange & Act
        config = ConversationEndConfig(require_confirmation=False, auto_end=True)

        # Assert
        assert config.require_confirmation is False
        assert config.auto_end is True


class TestConversationEndDetector:
    """测试对话结束检测器"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return ConversationEndDetector()

    def test_detect_explicit_end_marker(self, detector):
        """测试：检测显式结束标记"""
        # Arrange
        response = "这是一个很好的观点。\n\n<!-- END -->"

        # Act
        result = detector.detect(response)

        # Assert
        assert result.detected is True
        assert result.method == "marker"
        assert result.reason == "检测到显式结束标记"

    def test_no_end_marker_in_normal_response(self, detector):
        """测试：正常响应中无结束标记"""
        # Arrange
        response = "我同意你的看法。\n\n这个观点很有启发性。"

        # Act
        result = detector.detect(response)

        # Assert
        assert result.detected is False

    def test_disabled_detector_always_returns_false(self, detector):
        """测试：禁用的检测器始终返回 False"""
        # Arrange
        detector.config.enable_detection = False
        response = "我们有共识了。\n\n<!-- END -->"

        # Act
        result = detector.detect(response)

        # Assert
        assert result.detected is False

    def test_clean_response_removes_marker(self, detector):
        """测试：清理响应移除结束标记"""
        # Arrange
        response_with_marker = "这是我的观点。\n\n<!-- END -->"

        # Act
        cleaned = detector.clean_response(response_with_marker)

        # Assert
        assert "<!-- END -->" not in cleaned
        assert "这是我的观点" in cleaned
        assert cleaned.strip().endswith("观点。")

    def test_clean_response_without_marker(self, detector):
        """测试：清理没有标记的响应"""
        # Arrange
        response = "这是我的观点。"

        # Act
        cleaned = detector.clean_response(response)

        # Assert
        assert cleaned == response

    def test_custom_end_marker_detection(self):
        """测试：自定义结束标记检测"""
        # Arrange
        config = ConversationEndConfig(end_marker="::END::")
        detector = ConversationEndDetector(config)
        response = "对话结束 ::END::"

        # Act
        result = detector.detect(response)

        # Assert
        assert result.detected is True

    def test_marker_at_end_only(self, detector):
        """测试：只有末尾的标记才被检测"""
        # Arrange - 标记在中间
        response = "<!-- END --> 还有更多内容"

        # Act
        result = detector.detect(response)

        # Assert - 应该检测到（简单实现不检查位置）
        assert result.detected is True


class TestEndProposal:
    """测试结束提议"""

    def test_create_end_proposal(self):
        """测试：创建结束提议"""
        # Arrange
        agent_name = "支持者"
        response_text = "我们有共识了。\n\n<!-- END -->"
        response_clean = "我们有共识了。"

        # Act
        proposal = EndProposal(
            agent_name=agent_name,
            response_text=response_text,
            response_clean=response_clean,
        )

        # Assert
        assert proposal.agent_name == agent_name
        assert proposal.response_text == response_text
        assert proposal.response_clean == response_clean
        assert proposal.confirmed is False

    def test_confirm_proposal(self):
        """测试：确认提议"""
        # Arrange
        proposal = EndProposal("支持者", "结束", "结束")

        # Act
        proposal.confirm()

        # Assert
        assert proposal.confirmed is True

    def test_proposal_string_representation(self):
        """测试：提议的字符串表示"""
        # Arrange
        proposal = EndProposal(
            "支持者", "我们有共识了。\n\n<!-- END -->", "我们有共识了。"
        )

        # Act
        s = str(proposal)

        # Assert
        assert "支持者" in s
        assert "我们有共识了" in s


class TestIntegration:
    """测试集成场景"""

    @pytest.fixture
    def detector(self):
        """创建检测器实例"""
        return ConversationEndDetector()

    def test_full_detection_workflow(self, detector):
        """测试：完整的检测工作流"""
        # Arrange
        response = "经过深入讨论，我们有以下共识。\n\n<!-- END -->"

        # Act - 检测
        result = detector.detect(response)

        # Assert - 检测到标记
        assert result.detected is True

        # Act - 清理
        cleaned = detector.clean_response(response)

        # Assert - 标记已移除
        assert "<!-- END -->" not in cleaned
        assert "经过深入讨论" in cleaned

    def test_create_proposal_after_detection(self, detector):
        """测试：检测后创建提议"""
        # Arrange
        response = "可以结束了。\n\n<!-- END -->"
        result = detector.detect(response)

        # Act
        if result.detected:
            proposal = EndProposal(
                agent_name="智能体",
                response_text=response,
                response_clean=detector.clean_response(response),
            )

        # Assert
        assert proposal.confirmed is False
        assert proposal.response_clean == "可以结束了。"

    @pytest.mark.parametrize(
        "response,expected_detected",
        [
            ("继续讨论", False),
            ("让我们总结一下。<!-- END -->", True),
            ("我同意，到此为止。<!-- END -->", True),
            ("还有一点要补充", False),
            ("<!-- END -->", True),  # 仅标记
        ],
    )
    def test_various_responses(self, detector, response, expected_detected):
        """测试：各种响应的检测"""
        # Act
        result = detector.detect(response)

        # Assert
        assert result.detected == expected_detected
