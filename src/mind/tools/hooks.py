"""
Hook 回调实现

提供各种 Hook 回调函数：
- PreToolUse: 工具调用前的权限检查
- PostToolUse: 工具调用后的使用统计
- Stop: 对话停止时的资源清理和结束评估
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from claude_agent_sdk.types import (
    HookContext,
    HookJSONOutput,
    PostToolUseHookInput,
    PreToolUseHookInput,
)

from mind.logger import get_logger

if TYPE_CHECKING:
    from anthropic.types import MessageParam

logger = get_logger("mind.hooks")


@dataclass
class ConversationEndCriteria:
    """对话结束评估标准

    定义对话被认为"完成"的各种条件。
    """

    # 最小轮数要求（防止过早结束）
    min_turns: int = 20

    # 是否需要用户确认
    require_confirmation: bool = True

    # 检查最后 N 轮是否有新内容（检测循环）
    check_last_n_turns: int = 5

    # 最短响应长度（字符数）
    min_response_length: int = 30


class ToolHooks:
    """工具 Hook 管理器

    管理所有工具相关的 Hook 回调，包括对话结束检测。
    """

    def __init__(self, end_criteria: ConversationEndCriteria | None = None):
        """初始化 Hook 管理器

        Args:
            end_criteria: 对话结束评估标准
        """
        self._tool_usage_count: dict[str, int] = {}
        self._tool_errors: dict[str, int] = {}
        self._end_criteria = end_criteria or ConversationEndCriteria()

        # 对话状态跟踪
        self._conversation_turn: int = 0
        self._last_responses: list[str] = []

    def set_conversation_state(self, turn: int, messages: list["MessageParam"]) -> None:
        """设置对话状态（供外部调用）

        Args:
            turn: 当前轮次
            messages: 对话历史
        """
        self._conversation_turn = turn

        # 提取最近的响应（用于检测循环）
        recent_responses = []
        for msg in reversed(messages[-self._end_criteria.check_last_n_turns * 2 :]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # 移除可能的标记和前缀
                    clean_content = content.replace("<!-- END -->", "")
                    clean_content = clean_content.split("\n")[0]  # 只取第一行
                    recent_responses.append(clean_content.strip())

        self._last_responses = recent_responses

    def _should_end_conversation(self) -> tuple[bool, str]:
        """评估对话是否应该结束

        Returns:
            (是否应该结束, 原因说明)
        """
        # 1. 检查轮数要求
        if self._conversation_turn < self._end_criteria.min_turns:
            return False, (
                f"轮数不足 ({self._conversation_turn} < {self._end_criteria.min_turns})"
            )

        # 2. 检查响应长度（避免过短的响应）
        if self._last_responses:
            last_response = self._last_responses[0]
            if len(last_response) < self._end_criteria.min_response_length:
                return False, (
                    f"响应过短 ({len(last_response)} "
                    f"< {self._end_criteria.min_response_length})"
                )

        # 3. 检测循环（最近几轮响应是否重复）
        if len(self._last_responses) >= 3:
            unique_responses = set(self._last_responses[:3])
            if len(unique_responses) <= 1:
                return True, "检测到对话循环（响应重复）"

        # 4. 默认不结束（让显式标记或其他机制决定）
        return False, "未满足结束条件"

    async def pre_tool_use(
        self,
        input: PreToolUseHookInput,
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookJSONOutput:
        """工具调用前 Hook

        Args:
            input: Hook 输入数据
            tool_use_id: 工具使用 ID
            context: Hook 上下文

        Returns:
            Hook 输出
        """
        tool_name = input.get("tool_name", "unknown")
        tool_input = input.get("tool_input", {})

        logger.debug(f"[PreToolUse] 工具: {tool_name}, 输入: {tool_input}")

        # 权限检查（可以根据 tool_name 决定是否允许）
        # 默认允许所有工具
        return {
            "continue_": True,
            "suppressOutput": False,
        }

    async def post_tool_use(
        self,
        input: PostToolUseHookInput,
        tool_use_id: str | None,
        context: HookContext,
    ) -> HookJSONOutput:
        """工具调用后 Hook

        Args:
            input: Hook 输入数据
            tool_use_id: 工具使用 ID
            context: Hook 上下文

        Returns:
            Hook 输出
        """
        tool_name = input.get("tool_name", "unknown")
        tool_response = input.get("tool_response")

        # 记录使用统计
        self._tool_usage_count[tool_name] = self._tool_usage_count.get(tool_name, 0) + 1

        response_len = len(str(tool_response)) if tool_response else 0
        logger.debug(f"[PostToolUse] 工具: {tool_name}, 响应长度: {response_len}")

        # 检查是否出错
        if tool_response and isinstance(tool_response, dict):
            if tool_response.get("is_error"):
                self._tool_errors[tool_name] = self._tool_errors.get(tool_name, 0) + 1
                error_msg = tool_response.get("content", "Unknown error")
                logger.warning(f"工具 {tool_name} 调用出错: {error_msg}")

        return {
            "continue_": True,
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": f"工具 {tool_name} 已使用 {self._tool_usage_count[tool_name]} 次",  # noqa: E501
            },
        }

    def get_usage_stats(self) -> dict[str, dict[str, int]]:
        """获取使用统计

        Returns:
            统计信息字典
        """
        return {
            "usage_count": self._tool_usage_count.copy(),
            "error_count": self._tool_errors.copy(),
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._tool_usage_count.clear()
        self._tool_errors.clear()
