"""
Hook 回调实现

提供各种 Hook 回调函数：
- PreToolUse: 工具调用前的权限检查
- PostToolUse: 工具调用后的使用统计
- Stop: 对话停止时的资源清理
"""

from claude_agent_sdk.types import (
    HookContext,
    HookJSONOutput,
    PostToolUseHookInput,
    PreToolUseHookInput,
)

from mind.logger import get_logger

logger = get_logger("mind.mcp_hooks")


class ToolHooks:
    """工具 Hook 管理器

    管理所有工具相关的 Hook 回调
    """

    def __init__(self):
        """初始化 Hook 管理器"""
        self._tool_usage_count: dict[str, int] = {}
        self._tool_errors: dict[str, int] = {}

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
