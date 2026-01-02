"""
对话结束检测模块（重新设计）

提供 AI 主动触发对话结束的能力：
- 显式结束标记检测
- 响应清理
- 结束提议管理
"""

from dataclasses import dataclass

from mind.logger import get_logger

logger = get_logger("mind.conversation_ending")

# 默认结束标记
DEFAULT_END_MARKER = "<!-- END -->"


@dataclass
class ConversationEndConfig:
    """对话结束检测配置"""

    # 是否启用检测
    enable_detection: bool = True

    # 显式结束标记
    end_marker: str = DEFAULT_END_MARKER

    # 是否需要用户确认
    require_confirmation: bool = True

    # 检测后是否自动结束（False 时仅提示用户）
    auto_end: bool = False

    # 检测结束前所需的最小轮数
    # 防止对话过早结束，确保双方充分交流
    min_turns_before_end: int = 20


@dataclass
class EndDetectionResult:
    """结束检测结果"""

    detected: bool
    method: str = "marker"  # 只支持显式标记
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

    只检测显式标记，不做语义猜测。
    充分利用 LLM 的判断能力。
    """

    def __init__(self, config: ConversationEndConfig | None = None) -> None:
        """初始化检测器

        Args:
            config: 检测器配置
        """
        self.config = config or ConversationEndConfig()

    def detect(self, response: str, current_turn: int = 0) -> EndDetectionResult:
        """检测响应中是否包含结束标记

        Args:
            response: AI 的完整响应文本
            current_turn: 当前对话轮次（从 1 开始），0 表示未指定

        Returns:
            结束检测结果
        """
        if not self.config.enable_detection:
            return EndDetectionResult(detected=False)

        # 检查是否达到最小轮数要求
        if current_turn < self.config.min_turns_before_end:
            logger.debug(
                f"轮次不足 ({current_turn} < {self.config.min_turns_before_end})，"
                "忽略结束标记"
            )
            return EndDetectionResult(detected=False)

        # 检测显式标记（简单、可靠、0 误判）
        if self.config.end_marker in response:
            logger.info(
                f"检测到显式结束标记 (第 {current_turn} 轮，"
                f"满足最小轮数要求 {self.config.min_turns_before_end})"
            )
            return EndDetectionResult(
                detected=True,
                method="marker",
                reason="检测到显式结束标记",
            )

        # 未检测到结束信号
        return EndDetectionResult(detected=False)

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
