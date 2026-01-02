"""
工具适配器 - 统一工具调用接口

提供统一的工具调用接口，自动在原始 ToolAgent 和 SDK ToolManager 之间选择。
"""

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from anthropic.types import MessageParam

from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.tools.sdk_tool_manager import SDKToolManager
    from mind.tools.tool_agent import ToolAgent

logger = get_logger("mind.tool_adapter")


@dataclass
class ToolAdapterConfig:
    """工具适配器配置"""

    # 是否使用 SDK 工具管理器
    use_sdk: bool = field(
        default_factory=lambda: os.getenv("MIND_USE_SDK_TOOLS", "false").lower()
        == "true"
    )

    # 是否启用 MCP
    enable_mcp: bool = field(
        default_factory=lambda: os.getenv("MIND_ENABLE_MCP", "true").lower() == "true"
    )

    # SDK 失败时是否降级到原始实现
    fallback_on_error: bool = True

    # 最大重试次数
    max_retries: int = 2


class ToolAdapter:
    """工具适配器 - 统一的工具调用接口

    提供以下功能：
    - 自动选择使用 SDK 或原始实现
    - 错误降级处理
    - 使用统计和监控
    """

    def __init__(self, config: ToolAdapterConfig | None = None):
        """初始化工具适配器

        Args:
            config: 适配器配置
        """
        self.config = config or ToolAdapterConfig()
        self._sdk_manager: SDKToolManager | None = None
        self._fallback_agent: ToolAgent | None = None
        self._stats: dict[str, int] = {
            "sdk_calls": 0,
            "fallback_calls": 0,
            "errors": 0,
        }

        # 延迟初始化
        if self.config.use_sdk:
            logger.info("工具适配器: 将使用 SDK 工具管理器")
        else:
            logger.info("工具适配器: 将使用原始 ToolAgent")

    async def initialize(self) -> None:
        """初始化工具适配器

        根据配置初始化 SDK 管理器或原始代理
        """
        if self.config.use_sdk:
            try:
                from mind.tools.sdk_tool_manager import SDKToolConfig, SDKToolManager

                sdk_config = SDKToolConfig(
                    enable_mcp=self.config.enable_mcp,
                )
                self._sdk_manager = SDKToolManager(config=sdk_config)
                await self._sdk_manager.initialize()
                logger.info("SDK 工具管理器初始化成功")
            except Exception as e:
                logger.error(f"SDK 工具管理器初始化失败: {e}")
                if not self.config.fallback_on_error:
                    raise
                logger.warning("将降级到原始 ToolAgent")
                self._sdk_manager = None

        # 始终准备降级代理
        if self.config.fallback_on_error:
            try:
                from mind.tools.tool_agent import ToolAgent

                self._fallback_agent = ToolAgent()
                logger.info("原始 ToolAgent 已准备作为降级选项")
            except Exception as e:
                logger.error(f"原始 ToolAgent 初始化失败: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        if self._sdk_manager:
            try:
                await self._sdk_manager.cleanup()
            except Exception as e:
                logger.error(f"SDK 清理失败: {e}")

    async def query_tool(
        self,
        question: str,
        messages: list[MessageParam],
        agent_name: str,
    ) -> str | None:
        """查询工具

        Args:
            question: 查询问题
            messages: 对话历史
            agent_name: 智能体名称

        Returns:
            工具返回结果，失败时返回 None
        """
        # 优先使用 SDK
        if self._sdk_manager:
            try:
                result = await self._query_sdk(question, messages, agent_name)
                if result is not None:
                    self._stats["sdk_calls"] += 1
                    return result
            except Exception as e:
                logger.error(f"SDK 工具调用失败: {e}")
                self._stats["errors"] += 1

                # 不降级，直接返回
                if not self.config.fallback_on_error:
                    return None

        # 降级到原始实现
        if self._fallback_agent:
            try:
                result = await self._query_fallback(question, messages, agent_name)
                if result is not None:
                    self._stats["fallback_calls"] += 1
                    return result
            except Exception as e:
                logger.error(f"降级工具调用失败: {e}")
                self._stats["errors"] += 1

        return None

    async def _query_sdk(
        self,
        question: str,
        messages: list[MessageParam],
        agent_name: str,
    ) -> str | None:
        """使用 SDK 查询工具"""
        if self._sdk_manager is None:
            raise RuntimeError("SDK 管理器未初始化")

        logger.debug(f"[SDK] {agent_name} 查询工具: {question}")
        return await self._sdk_manager.query_tool(question, messages, agent_name)

    async def _query_fallback(
        self,
        question: str,
        messages: list[MessageParam],
        agent_name: str,
    ) -> str | None:
        """使用原始 ToolAgent 查询"""
        if self._fallback_agent is None:
            raise RuntimeError("降级代理未初始化")

        logger.debug(f"[Fallback] {agent_name} 查询工具: {question}")
        return await self._fallback_agent.query_tool(question, messages)

    def get_stats(self) -> dict[str, int]:
        """获取使用统计

        Returns:
            统计信息字典
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "sdk_calls": 0,
            "fallback_calls": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()


# 便捷函数
async def create_tool_adapter(
    use_sdk: bool | None = None,
    enable_mcp: bool = True,
) -> ToolAdapter:
    """创建并初始化工具适配器

    Args:
        use_sdk: 是否使用 SDK，None 则从环境变量读取
        enable_mcp: 是否启用 MCP

    Returns:
        初始化完成的工具适配器
    """
    # 如果 use_sdk 为 None，让 ToolAdapterConfig 使用默认值（从环境变量读取）
    if use_sdk is None:
        config = ToolAdapterConfig(enable_mcp=enable_mcp)
    else:
        config = ToolAdapterConfig(use_sdk=use_sdk, enable_mcp=enable_mcp)
    adapter = ToolAdapter(config)
    await adapter.initialize()
    return adapter
