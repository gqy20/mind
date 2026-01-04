"""
对话结束检测模块（重新设计）

提供 AI 主动触发对话结束的能力：
- 显式结束标记检测
- 智能分析检测（循环检测、响应质量）
- 响应清理
- 结束提议管理
"""

from dataclasses import dataclass

from mind.logger import get_logger

logger = get_logger("mind.conversation.ending_detector")

# 默认结束标记
DEFAULT_END_MARKER = "<!-- END -->"

# 智能检测常量
# 检测循环所需的最少重复响应次数
_MIN_REPEAT_COUNT_FOR_LOOP = 3


@dataclass
class ConversationEndConfig:
    """对话结束检测配置"""

    # 是否启用检测
    enable_detection: bool = True

    # 显式结束标记
    end_marker: str = DEFAULT_END_MARKER

    # 检测结束前所需的最小轮数
    # 防止对话过早结束，确保双方充分交流
    min_turns_before_end: int = 20

    # ========== 智能分析检测配置（默认启用） ==========

    # 是否启用智能分析检测（默认启用）
    enable_analysis_detection: bool = True

    # 智能检测的最小轮数
    analysis_min_turns: int = 20

    # 最小响应长度（字符数）
    analysis_min_response_length: int = 30

    # 检查最近几轮的响应（用于循环检测）
    analysis_check_turns: int = 5


@dataclass
class EndDetectionResult:
    """结束检测结果"""

    detected: bool
    method: str = "marker"  # "marker" 或 "analysis"
    reason: str = "检测到显式结束标记"


@dataclass
class EndProposal:
    """结束提议

    当检测到结束时创建此提议，
    用于用户确认或自动执行。
    """

    agent_name: str
    response_text: str  # 完整响应（包含标记）
    response_clean: str  # 清理后的响应（移除标记）
    confirmed: bool = False

    def confirm(self) -> None:
        """用户确认结束"""
        self.confirmed = True
        logger.info(f"用户确认结束 {self.agent_name} 的提议")

    def __str__(self) -> str:
        """字符串表示"""
        status = "已确认" if self.confirmed else "待确认"
        return (
            f"[{self.agent_name}] 建议结束对话 (状态: {status})\n"
            f"内容: {self.response_clean}"
        )


class ConversationEndDetector:
    """对话结束检测器

    支持两种检测方式：
    1. 显式标记检测：检测 <!-- END --> 标记
    2. 智能分析检测：检测对话循环、响应质量等
    """

    def __init__(self, config: ConversationEndConfig | None = None) -> None:
        """初始化检测器

        Args:
            config: 检测器配置
        """
        self.config = config or ConversationEndConfig()
        # 用于智能检测的状态
        self._last_responses: list[str] = []

    def detect(
        self,
        response: str,
        current_turn: int = 0,
        messages: list | None = None,
    ) -> EndDetectionResult:
        """检测对话是否应该结束

        检测逻辑（两层验证机制）：
        1. 有显式标记 → 触发智能分析验证
        2. 无显式标记 → 智能分析检测

        Args:
            response: AI 的完整响应文本
            current_turn: 当前对话轮次（从 1 开始），0 表示未指定
            messages: 完整对话历史（用于智能分析，必需）

        Returns:
            结束检测结果
        """
        if not self.config.enable_detection:
            return EndDetectionResult(detected=False)

        has_marker = self.config.end_marker in response

        # 场景 1: 有显式标记 → 智能分析验证
        if has_marker:
            if current_turn >= self.config.min_turns_before_end:
                logger.info(
                    f"检测到显式结束标记 (第 {current_turn} 轮)，进行智能分析验证"
                )

                # 使用智能分析验证（默认启用）
                if self.config.enable_analysis_detection and messages is not None:
                    analysis_result = self._detect_by_analysis(messages, current_turn)
                    if analysis_result.detected:
                        # 智能分析认为应该结束
                        logger.info("智能分析验证通过，接受显式结束标记")
                        return EndDetectionResult(
                            detected=True,
                            method="marker_verified",
                            reason=f"显式标记 + {analysis_result.reason}",
                        )
                    else:
                        # 智能分析认为不应该结束，忽略显式标记
                        logger.info("智能分析验证未通过，忽略显式结束标记")
                        return EndDetectionResult(detected=False)
                else:
                    # 智能分析未启用或未提供 messages → 忽略显式标记
                    logger.warning("智能分析未启用或未提供对话历史，忽略显式结束标记")
                    return EndDetectionResult(detected=False)

        # 场景 2: 没有显式标记，但启用智能分析
        if (
            self.config.enable_analysis_detection
            and messages is not None
            and not has_marker
        ):
            return self._detect_by_analysis(messages, current_turn)

        # 未检测到结束信号
        return EndDetectionResult(detected=False)

    def _has_explicit_marker(self, response: str) -> bool:
        """检查响应中是否有显式结束标记"""
        return self.config.end_marker in response

    def _detect_by_analysis(
        self, messages: list, current_turn: int
    ) -> EndDetectionResult:
        """通过智能分析检测对话是否应该结束

        Args:
            messages: 对话历史
            current_turn: 当前轮次

        Returns:
            结束检测结果
        """
        # 1. 检查轮数要求
        if current_turn < self.config.analysis_min_turns:
            logger.debug(
                f"智能检测: 轮次不足 ({current_turn} < "
                f"{self.config.analysis_min_turns})"
            )
            return EndDetectionResult(detected=False)

        # 2. 更新响应历史
        self._update_response_history(messages)

        # 3. 检查响应长度
        if self._last_responses:
            last_response = self._last_responses[0]
            if len(last_response) < self.config.analysis_min_response_length:
                logger.debug(
                    f"智能检测: 响应过短 ({len(last_response)} < "
                    f"{self.config.analysis_min_response_length})"
                )
                return EndDetectionResult(detected=False)

        # 4. 检测对话循环
        loop_detected = self._detect_conversation_loop()
        if loop_detected:
            logger.info("智能检测: 检测到对话循环")
            return EndDetectionResult(
                detected=True,
                method="analysis",
                reason="检测到对话循环（响应重复）",
            )

        # 未满足结束条件
        return EndDetectionResult(detected=False)

    def _update_response_history(self, messages: list) -> None:
        """从消息历史中提取最近的响应

        用于智能分析检测，从对话历史中提取最近 N 轮的助手响应。
        每个响应只保留第一行，以简化比较（避免被细微差异干扰）。

        Args:
            messages: 完整对话历史
        """
        recent_responses = []
        check_count = self.config.analysis_check_turns

        # 从后向前提取最近的 assistant 响应
        # 切片 messages[-check_count * 2:] 确保有足够的消息（每轮包含 user+assistant）
        for msg in reversed(messages[-check_count * 2 :]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # 清理内容：移除结束标记，只保留第一行
                    clean_content = content.replace(self.config.end_marker, "")
                    first_line = clean_content.split("\n")[0].strip()
                    if first_line:
                        recent_responses.append(first_line)

        self._last_responses = recent_responses

    def _detect_conversation_loop(self) -> bool:
        """检测对话循环

        通过检查最近 N 个响应是否相同来判断是否陷入循环。
        如果响应过于单一（重复或相似），说明对话可能陷入僵局。

        Returns:
            是否检测到循环
        """
        if len(self._last_responses) < _MIN_REPEAT_COUNT_FOR_LOOP:
            return False

        # 检查最近 N 个响应是否相同（或只有一种独特响应）
        unique_responses = set(self._last_responses[:_MIN_REPEAT_COUNT_FOR_LOOP])
        return len(unique_responses) <= 1

    def clean_response(self, response: str) -> str:
        """清理响应（移除结束标记）用于显示

        Args:
            response: 原始响应

        Returns:
            清理后的响应
        """
        cleaned = response.replace(self.config.end_marker, "")
        # 移除可能的前后空行
        lines = [line for line in cleaned.split("\n") if line.strip()]
        return "\n".join(lines)
