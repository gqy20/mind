"""
Unit tests for Conversation Ending Detection (Redesigned)

测试对话结束检测功能（重新设计）：
- 显式标记检测（简单、可靠）
- 响应清理
- 结束提议管理
- 两轮过渡机制
- 集成测试
"""

import pytest

from mind.conversation.ending_detector import (
    ConversationEndConfig,
    ConversationEndDetector,
    EndDetectionResult,
    EndProposal,
)


class TestConversationEndConfig:
    """测试对话结束配置类"""

    def test_default_config(self):
        """测试：默认配置值（智能分析已启用，最小轮数 10）"""
        # Arrange & Act
        config = ConversationEndConfig()

        # Assert - 智能分析默认启用
        assert config.enable_detection is True
        assert config.end_marker == "<!-- END -->"
        assert config.enable_analysis_detection is True  # 默认启用
        assert config.min_turns_before_end == 10  # 修改为 10

    def test_analysis_detection_enabled_by_default(self):
        """测试：智能分析检测默认启用"""
        # Arrange & Act
        config = ConversationEndConfig()

        # Assert - 智能分析相关配置的默认值
        assert config.enable_analysis_detection is True
        assert config.analysis_min_turns == 10
        assert config.analysis_end_threshold == 80
        assert config.analysis_warning_threshold == 60
        assert config.transition_turns == 2

    def test_custom_min_turns(self):
        """测试：自定义最小轮数"""
        # Arrange & Act
        config = ConversationEndConfig(min_turns_before_end=10)

        # Assert
        assert config.min_turns_before_end == 10

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
    """测试对话结束检测器（基础功能测试）

    新的验证机制：显式标记必须有智能分析验证（需要 messages 参数）。
    这些测试验证新机制的行为。
    """

    @pytest.fixture
    def detector(self):
        """创建检测器实例（无轮数限制，智能分析启用）"""
        config = ConversationEndConfig(
            min_turns_before_end=0, enable_analysis_detection=True
        )
        return ConversationEndDetector(config)

    def test_detect_sync_simple_marker_detection(self, detector):
        """测试：同步 detect() 方法简单检查显式标记"""
        # Arrange
        response = "这是一个很好的观点。\n\n<!-- END -->"

        # Act - 同步方法只需要标记和轮数
        result = detector.detect(response, current_turn=1)

        # Assert - 同步版本直接检测标记（不需要 AI 验证）
        assert result.detected is True
        assert result.method == "marker"
        assert result.transition == 2  # 默认过渡轮数

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
        config = ConversationEndConfig(end_marker="::END::", min_turns_before_end=0)
        detector = ConversationEndDetector(config)
        response = "对话结束 ::END::"

        # Act - 同步方法直接检测标记
        result = detector.detect(response, current_turn=1)

        # Assert - 检测到自定义标记
        assert result.detected is True
        assert result.method == "marker"

    def test_marker_at_end_only(self, detector):
        """测试：标记在任何位置都会被检测到"""
        # Arrange - 标记在中间
        response = "<!-- END --> 还有更多内容"

        # Act - 同步方法检测标记
        result = detector.detect(response, current_turn=1)

        # Assert - 标记被检测到（标记可以在任何位置）
        assert result.detected is True

    def test_end_marker_ignored_when_turn_count_too_low(self):
        """测试：轮次不足时，结束标记被忽略"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "可以结束了。\n\n<!-- END -->"

        # Act - 第 1 轮
        result = detector.detect(response, current_turn=1)

        # Assert - 不应该检测到（轮次不足）
        assert result.detected is False

    def test_end_marker_detected_when_turn_count_sufficient(self):
        """测试：轮次足够时检测到标记"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "可以结束了。\n\n<!-- END -->"

        # Act - 第 20 轮（达到最小轮数）
        result = detector.detect(response, current_turn=20)

        # Assert - 同步方法检测到标记
        assert result.detected is True
        assert result.method == "marker"

    def test_end_marker_detected_after_min_turns(self):
        """测试：超过最小轮数时检测到标记"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "达成共识。\n\n<!-- END -->"

        # Act - 第 25 轮（超过最小轮数）
        result = detector.detect(response, current_turn=25)

        # Assert - 同步方法检测到标记
        assert result.detected is True

    def test_turn_count_edge_case_exactly_min_turns(self):
        """测试：边界情况 - 刚好等于最小轮数"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "对话完成。<!-- END -->"

        # Act - 第 20 轮（刚好等于最小值）
        result = detector.detect(response, current_turn=20)

        # Assert - 同步方法检测到标记（刚好达到最小轮数）
        assert result.detected is True

    def test_turn_count_edge_case_one_below_min_turns(self):
        """测试：边界情况 - 少一轮"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "对话完成。<!-- END -->"

        # Act - 第 19 轮（少一轮）
        result = detector.detect(response, current_turn=19)

        # Assert - 不应该检测到
        assert result.detected is False

    def test_no_turn_count_param_defaults_to_zero(self):
        """测试：不传轮次参数时，默认为 0"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "结束吧。<!-- END -->"

        # Act - 不传轮次参数（默认为 0）
        result = detector.detect(response)

        # Assert - 不应该检测到（0 < 20）
        assert result.detected is False


class TestConversationEndDetectorAnalysis:
    """测试对话结束检测器的智能分析功能

    注意：智能分析需要使用 detect_async() 方法，因为需要调用 AI API。
    这里主要测试同步的 detect() 方法的基本标记检测行为。
    """

    @pytest.fixture
    def detector_with_analysis(self):
        """创建启用智能分析的检测器"""
        config = ConversationEndConfig(
            min_turns_before_end=0,
            enable_analysis_detection=True,
            analysis_min_turns=5,
        )
        return ConversationEndDetector(config)

    def test_detect_sync_only_checks_marker_not_analysis(self, detector_with_analysis):
        """测试：同步 detect() 方法只检查标记，不执行 AI 分析"""
        # Arrange
        long_response = "我完全同意这个观点，这是一个非常好的论述，值得深入探讨。"
        response = f"{long_response}\n\n<!-- END -->"

        # Act - 同步方法只检查标记，不检查 messages
        result = detector_with_analysis.detect(response, current_turn=6)

        # Assert - 同步方法检测到标记（不进行 AI 分析验证）
        assert result.detected is True
        assert result.method == "marker"

    def test_analysis_detection_when_turn_count_insufficient(
        self, detector_with_analysis
    ):
        """测试：轮次不足时，标记不被检测"""
        # Arrange
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "结束<!-- END -->"

        # Act - 第 2 轮，不足最小轮数
        result = detector.detect(response, current_turn=2)

        # Assert - 不应该检测到（轮次不足）
        assert result.detected is False

    def test_analysis_detection_disabled_when_flag_false(self):
        """测试：禁用检测时不触发"""
        # Arrange - 禁用检测
        config = ConversationEndConfig(
            enable_detection=False,
        )
        detector = ConversationEndDetector(config)
        response = "结束<!-- END -->"

        # Act
        result = detector.detect(response, current_turn=10)

        # Assert - 不应该检测到（检测已禁用）
        assert result.detected is False

    def test_explicit_marker_detected_by_sync_method(self, detector_with_analysis):
        """测试：同步方法检测显式标记（不需要 AI 验证）"""
        # Arrange - 有显式标记
        long_response = "我完全同意这个观点，这是一个非常好的论述。"
        response = f"讨论完毕 {long_response}<!-- END -->"

        # Act - 同步方法直接检测标记
        result = detector_with_analysis.detect(response, current_turn=6)

        # Assert - 同步方法检测到标记（不进行 AI 分析验证）
        assert result.detected is True
        assert result.method == "marker"

    def test_normal_response_without_marker_no_detection(self, detector_with_analysis):
        """测试：正常响应（无标记）不会被检测为结束"""
        # Arrange - 正常响应
        response = "这是一个很好的观点，我同意。"

        # Act
        result = detector_with_analysis.detect(response, current_turn=6)

        # Assert - 不应该检测到
        assert result.detected is False

    def test_marker_detection_with_sufficient_turns(self, detector_with_analysis):
        """测试：轮次足够时检测到标记"""
        # Arrange
        response = "达成共识。<!-- END -->"

        # Act - 轮次足够
        result = detector_with_analysis.detect(response, current_turn=10)

        # Assert - 同步方法检测到标记
        assert result.detected is True
        assert result.method == "marker"

    def test_marker_insufficient_turns_even_with_analysis(self, detector_with_analysis):
        """测试：轮次不足时，即使有显式标记也不检测"""
        # Arrange - 设置较高的最小轮数
        config = ConversationEndConfig(min_turns_before_end=20)
        detector = ConversationEndDetector(config)
        response = "可以结束<!-- END -->"

        # Act - 第 3 轮（低于 min_turns_before_end=20）
        result = detector.detect(response, current_turn=3)

        # Assert - 不应该检测到（轮次不足）
        assert result.detected is False


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
    """测试集成场景（基础功能测试）

    测试同步 detect() 方法的行为。
    """

    @pytest.fixture
    def detector(self):
        """创建检测器实例（智能分析启用）"""
        config = ConversationEndConfig(
            min_turns_before_end=0, enable_analysis_detection=True
        )
        return ConversationEndDetector(config)

    def test_full_detection_workflow_with_marker(self, detector):
        """测试：完整的检测流程（带标记）"""
        # Arrange
        response = "经过深入讨论，我们有以下共识。\n\n<!-- END -->"

        # Act - 同步方法检测标记
        result = detector.detect(response, current_turn=1)

        # Assert - 检测到标记
        assert result.detected is True

        # 清理功能仍然正常工作
        cleaned = detector.clean_response(response)
        assert "<!-- END -->" not in cleaned
        assert "经过深入讨论" in cleaned

    def test_clean_response_still_works(self, detector):
        """测试：清理响应功能不受影响"""
        # Arrange
        response = "可以结束了。\n\n<!-- END -->"

        # Act
        cleaned = detector.clean_response(response)

        # Assert - 清理功能正常工作
        assert cleaned == "可以结束了。"

    @pytest.mark.parametrize(
        "response,expected_detected",
        [
            ("继续讨论", False),
            ("让我们总结一下。<!-- END -->", True),  # 有标记，检测到
            ("我同意，到此为止。<!-- END -->", True),  # 有标记，检测到
            ("还有一点要补充", False),
            ("<!-- END -->", True),  # 有标记，检测到
        ],
    )
    def test_various_responses(self, detector, response, expected_detected):
        """测试：各种响应的检测"""
        # Act - 同步方法检测标记
        result = detector.detect(response, current_turn=1)

        # Assert
        assert result.detected == expected_detected


class TestTransitionMechanism:
    """测试两轮过渡机制

    新机制：检测到结束时，先进行两轮过渡对话，然后真正结束。
    """

    def test_end_detection_result_supports_transition(self):
        """测试：EndDetectionResult 支持 transition 字段"""
        # Arrange & Act
        result = EndDetectionResult(
            detected=True,
            method="marker_verified",
            reason="检测到循环",
            transition=2,  # 需要两轮过渡
        )

        # Assert
        assert result.detected is True
        assert result.transition == 2
        assert result.method == "marker_verified"

    def test_end_detection_result_without_transition(self):
        """测试：EndDetectionResult 可以没有 transition（向后兼容）"""
        # Arrange & Act
        result = EndDetectionResult(detected=False)

        # Assert
        assert result.detected is False
        # transition 应该默认为 None 或 0
        assert result.transition == 0
