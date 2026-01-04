"""
对话结束检测模块（重新设计）

提供 AI 主动触发对话结束的能力：
- 显式结束标记检测
- AI 智能分析检测（LLM 判断对话质量）
- 响应清理
- 结束提议管理
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from mind.logger import get_logger

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

logger = get_logger("mind.conversation.ending_detector")

# 默认结束标记
DEFAULT_END_MARKER = "<!-- END -->"


@dataclass
class AnalysisResult:
    """AI 分析结果

    Attributes:
        should_end: 是否应该结束对话
        score: 总评分（0-100）
        threshold: 结束阈值
        reason: 分析原因说明
        loop_score: 循环程度评分（0-30）
        consensus_score: 共识达成评分（0-40）
        expression_score: 观点充分性评分（0-30）
    """

    should_end: bool
    score: int
    threshold: int
    reason: str
    loop_score: int
    consensus_score: int
    expression_score: int

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisResult":
        """从字典创建 AnalysisResult

        Args:
            data: 包含分析结果的字典

        Returns:
            AnalysisResult 实例
        """
        return cls(
            should_end=data.get("should_end", False),
            score=data.get("score", 0),
            threshold=data.get("threshold", 80),
            reason=data.get("reason", ""),
            loop_score=data.get("loop_score", 0),
            consensus_score=data.get("consensus_score", 0),
            expression_score=data.get("expression_score", 0),
        )


@dataclass
class ConversationEndConfig:
    """对话结束检测配置"""

    # 是否启用检测
    enable_detection: bool = True

    # 显式结束标记
    end_marker: str = DEFAULT_END_MARKER

    # 检测结束前所需的最小轮数
    # 防止对话过早结束，确保双方充分交流
    min_turns_before_end: int = 10

    # ========== AI 智能分析检测配置 ==========

    # 是否启用 AI 分析检测（默认启用）
    enable_analysis_detection: bool = True

    # AI 检测的最小轮数
    analysis_min_turns: int = 10

    # AI 分析评分阈值（达到此分数触发结束）
    analysis_end_threshold: int = 80

    # AI 分析警告阈值（用于日志记录）
    analysis_warning_threshold: int = 60

    # AI 分析使用的模型
    analysis_model: str = "claude-sonnet-4-5-20250929"

    # ========== 过渡机制配置 ==========

    # 检测到结束后需要的过渡轮数（0 表示立即结束）
    transition_turns: int = 2


@dataclass
class EndDetectionResult:
    """结束检测结果

    Attributes:
        detected: 是否检测到结束信号
        method: 检测方法 ("marker", "ai_analysis", "marker_verified")
        reason: 检测原因说明
        transition: 需要的过渡轮数（0 表示立即结束，>0 表示需要过渡对话）
        analysis_score: AI 分析评分（如果有）
    """

    detected: bool
    method: str = "marker"  # "marker" 或 "ai_analysis"
    reason: str = "检测到显式结束标记"
    transition: int = 0  # 默认 0，表示立即结束
    analysis_score: int | None = None  # AI 分析评分


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
    2. AI 智能分析检测：使用 LLM 判断对话质量
    """

    def __init__(
        self,
        config: ConversationEndConfig | None = None,
        client: "AsyncAnthropic | None" = None,
    ) -> None:
        """初始化检测器

        Args:
            config: 检测器配置
            client: Anthropic 客户端（用于 AI 分析）
        """
        self.config = config or ConversationEndConfig()
        self._client = client

    def detect(
        self,
        response: str,
        current_turn: int = 0,
        messages: list | None = None,
    ) -> EndDetectionResult:
        """检测对话是否应该结束（同步版本，不支持 AI 分析）

        注意：此方法不支持 AI 分析，只能检测显式标记。
        如需 AI 分析功能，请使用 detect_async 方法。

        Args:
            response: AI 的完整响应文本
            current_turn: 当前对话轮次（从 1 开始），0 表示未指定
            messages: 完整对话历史（此参数在同步模式下被忽略）

        Returns:
            结束检测结果
        """
        if not self.config.enable_detection:
            return EndDetectionResult(detected=False)

        has_marker = self.config.end_marker in response

        # 同步模式：只支持显式标记检测（不带 AI 分析验证）
        if has_marker and current_turn >= self.config.min_turns_before_end:
            logger.info(
                f"检测到显式结束标记 (第 {current_turn} 轮)，"
                "同步模式直接接受（不进行 AI 分析验证）"
            )
            return EndDetectionResult(
                detected=True,
                method="marker",
                reason="检测到显式结束标记",
                transition=self.config.transition_turns,
            )

        # 未检测到结束信号
        return EndDetectionResult(detected=False)

    def _has_explicit_marker(self, response: str) -> bool:
        """检查响应中是否有显式结束标记"""
        return self.config.end_marker in response

    async def detect_async(
        self,
        response: str,
        current_turn: int = 0,
        messages: list | None = None,
    ) -> EndDetectionResult:
        """异步检测对话是否应该结束（支持 AI 分析）

        检测逻辑（两层验证机制）：
        1. 有显式标记 → 触发 AI 分析验证
        2. 无显式标记 → 可选的 AI 分析检测

        Args:
            response: AI 的完整响应文本
            current_turn: 当前对话轮次（从 1 开始），0 表示未指定
            messages: 完整对话历史（用于 AI 分析，必需）

        Returns:
            结束检测结果
        """
        if not self.config.enable_detection:
            return EndDetectionResult(detected=False)

        has_marker = self.config.end_marker in response

        # 场景 1: 有显式标记 → AI 分析验证
        if has_marker:
            if current_turn >= self.config.min_turns_before_end:
                logger.info(
                    f"检测到显式结束标记 (第 {current_turn} 轮)，进行 AI 分析验证"
                )

                # 使用 AI 分析验证（默认启用）
                if self.config.enable_analysis_detection and messages is not None:
                    if self._client is None:
                        logger.warning("未提供 Anthropic 客户端，跳过 AI 分析")
                        return EndDetectionResult(detected=False)

                    analysis_result = await self._analyze_by_ai(messages, current_turn)

                    # 记录评分信息
                    if analysis_result.score >= self.config.analysis_warning_threshold:
                        score_msg = (
                            f"AI 分析评分: {analysis_result.score}/"
                            f"{analysis_result.threshold} - {analysis_result.reason}"
                        )
                        logger.info(score_msg)

                    if analysis_result.should_end:
                        # AI 分析认为应该结束，返回带过渡轮数的结果
                        logger.info("AI 分析验证通过，接受显式结束标记，进入过渡期")
                        return EndDetectionResult(
                            detected=True,
                            method="marker_verified",
                            reason=f"显式标记 + {analysis_result.reason}",
                            transition=self.config.transition_turns,
                            analysis_score=analysis_result.score,
                        )
                    else:
                        # AI 分析认为不应该结束，忽略显式标记
                        fail_msg = (
                            f"AI 分析验证未通过 (评分: {analysis_result.score} < "
                            f"阈值: {analysis_result.threshold})，忽略显式结束标记"
                        )
                        logger.info(fail_msg)
                        return EndDetectionResult(detected=False)
                else:
                    # AI 分析未启用或未提供 messages → 忽略显式标记
                    logger.warning("AI 分析未启用或未提供对话历史，忽略显式结束标记")
                    return EndDetectionResult(detected=False)

        # 场景 2: 没有显式标记，但启用 AI 分析
        if (
            self.config.enable_analysis_detection
            and messages is not None
            and not has_marker
        ):
            if self._client is None:
                return EndDetectionResult(detected=False)

            analysis_result = await self._analyze_by_ai(messages, current_turn)
            if analysis_result.should_end:
                logger.info(f"AI 分析检测到对话应结束: {analysis_result.reason}")
                return EndDetectionResult(
                    detected=True,
                    method="ai_analysis",
                    reason=analysis_result.reason,
                    transition=self.config.transition_turns,
                    analysis_score=analysis_result.score,
                )

        # 未检测到结束信号
        return EndDetectionResult(detected=False)

    async def _analyze_by_ai(self, messages: list, current_turn: int) -> AnalysisResult:
        """使用 AI 分析对话是否应该结束

        Args:
            messages: 对话历史
            current_turn: 当前轮次

        Returns:
            AI 分析结果
        """
        # 1. 检查轮数要求
        if current_turn < self.config.analysis_min_turns:
            logger.debug(
                f"AI 分析: 轮次不足 ({current_turn} < {self.config.analysis_min_turns})"
            )
            return AnalysisResult(
                should_end=False,
                score=0,
                threshold=self.config.analysis_end_threshold,
                reason=f"轮次不足（{current_turn} < {self.config.analysis_min_turns}）",
                loop_score=0,
                consensus_score=0,
                expression_score=0,
            )

        # 2. 准备最近几轮对话用于分析
        recent_messages = messages[-10:]  # 最近 10 条消息
        conversation_text = "\n".join(
            [
                f"{msg.get('role', '')}: {msg.get('content', '')}"
                for msg in recent_messages
            ]
        )

        # 3. 构建 AI 分析提示词
        analysis_prompt = f"""你是一个对话质量分析专家。请分析以下对话是否应该结束。

## 对话历史（最近 {len(recent_messages)} 条消息）

{conversation_text}

## 当前轮次
第 {current_turn} 轮

## 分析维度

请从以下三个维度评分（0-100分制）：

1. **循环程度（0-30分）**
   - 0分：对话内容新颖，各有新观点
   - 15分：有些观点重复，但仍有新内容
   - 30分：对话陷入循环，反复重复相同观点

2. **共识达成（0-40分）**
   - 0分：完全无共识，双方在激烈争论
   - 20分：部分共识，但仍有分歧
   - 40分：达成明确共识（双方都认可某种结论）或明确分歧（双方都同意保留不同意见）

3. **观点充分性（0-30分）**
   - 0分：观点尚未充分表达
   - 15分：观点基本表达，但仍有深入空间
   - 30分：双方观点已充分表达完整

## 判断标准

- 总分 ≥ {self.config.analysis_end_threshold}：建议结束对话
- 总分 < {self.config.analysis_end_threshold}：继续对话

## 输出格式

请严格按照以下 JSON 格式输出（不要添加任何其他文字）：

{{
  "should_end": true/false,
  "score": 总分（0-100）,
  "threshold": {self.config.analysis_end_threshold},
  "reason": "简短原因说明（20字以内）",
  "loop_score": 循环程度评分（0-30）,
  "consensus_score": 共识达成评分（0-40）,
  "expression_score": 观点充分性评分（0-30）
}}
"""

        try:
            # 4. 调用 Claude API 进行分析
            # 类型检查：self._client 已在前置检查中确认为非 None
            if self._client is None:
                raise ValueError("Client is None")
            response = await self._client.messages.create(
                model=self.config.analysis_model,
                max_tokens=1024,
                messages=[{"role": "user", "content": analysis_prompt}],
            )

            # 5. 提取 JSON 响应
            # 类型检查：假设响应的第一块是 TextBlock
            first_block = response.content[0]
            if hasattr(first_block, "text"):
                content = first_block.text.strip()
            else:
                raise ValueError(f"Unexpected block type: {type(first_block)}")

            # 尝试提取 JSON（处理可能的 markdown 代码块）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(content)
            analysis_result = AnalysisResult.from_dict(result_dict)

            logger.info(
                f"AI 分析完成: should_end={analysis_result.should_end}, "
                f"score={analysis_result.score}/{analysis_result.threshold}, "
                f"reason={analysis_result.reason}"
            )

            return analysis_result

        except json.JSONDecodeError as e:
            logger.error(f"AI 分析响应解析失败: {e}, 响应内容: {content[:200]}")
            # 解析失败时返回默认结果（不结束）
            return AnalysisResult(
                should_end=False,
                score=0,
                threshold=self.config.analysis_end_threshold,
                reason="AI 分析解析失败",
                loop_score=0,
                consensus_score=0,
                expression_score=0,
            )
        except Exception as e:
            logger.exception(f"AI 分析调用失败: {e}")
            # 调用失败时返回默认结果（不结束）
            return AnalysisResult(
                should_end=False,
                score=0,
                threshold=self.config.analysis_end_threshold,
                reason=f"AI 分析调用失败: {str(e)[:50]}",
                loop_score=0,
                consensus_score=0,
                expression_score=0,
            )

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
