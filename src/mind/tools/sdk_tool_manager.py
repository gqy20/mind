"""
SDK 工具管理器 - 基于 Claude Agent SDK 的工具管理

提供以下功能：
- MCP 服务器集成
- Hook 系统支持
- 工具权限控制
- 使用统计和监控
"""

from dataclasses import dataclass, field
from typing import Any

from anthropic.types import MessageParam
from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import HookMatcher

from mind.logger import get_logger

logger = get_logger("mind.sdk_tool_manager")


@dataclass
class SDKToolConfig:
    """SDK 工具配置"""

    # 是否启用 MCP
    enable_mcp: bool = True

    # 工具权限配置
    tool_permissions: dict[str, str] = field(default_factory=dict)

    # Hook 超时时间（秒）
    hook_timeout: float = 30.0

    # 最大预算（美元）
    max_budget_usd: float | None = None

    # 是否启用 Hooks
    enable_hooks: bool = True


class SDKToolManager:
    """SDK 工具管理器

    管理 ClaudeSDKClient、MCP 服务器和 Hook 回调
    """

    def __init__(self, config: SDKToolConfig):
        """初始化 SDK 工具管理器

        Args:
            config: SDK 工具配置
        """
        self.config = config
        self._client: Any = None  # ClaudeSDKClient
        self._mcp_servers: dict[str, Any] = {}
        self._tool_usage_stats: dict[str, int] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """初始化 SDK 工具管理器"""
        if self._initialized:
            return

        try:
            # 导入 SDK（延迟导入以避免硬依赖）
            from claude_agent_sdk import ClaudeSDKClient

            # 构建 MCP 服务器配置
            mcp_servers = {}
            if self.config.enable_mcp:
                mcp_servers = await self._setup_mcp_servers()

            # 构建 Hook 配置
            hooks = None
            if self.config.enable_hooks:
                hooks = await self._setup_hooks()

            # 创建 SDK 选项
            options = ClaudeAgentOptions(
                mcp_servers=mcp_servers,
                hooks=hooks,  # type: ignore[arg-type]
                max_budget_usd=self.config.max_budget_usd,
                permission_mode="default",
            )

            # 创建客户端
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect()

            self._initialized = True
            logger.info("SDK 工具管理器初始化成功")

        except ImportError as e:
            logger.error(f"无法导入 Claude Agent SDK: {e}")
            raise RuntimeError(
                "Claude Agent SDK 未安装。请运行: pip install claude-agent-sdk"
            ) from e

    async def _setup_mcp_servers(self) -> dict[str, Any]:
        """设置 MCP 服务器

        Returns:
            MCP 服务器配置字典
        """
        from mind.tools.mcp.servers import (
            create_code_analysis_mcp_server,
            create_knowledge_mcp_server,
            create_web_search_mcp_server,
        )

        servers = {}

        try:
            # 知识库 MCP
            knowledge_server = create_knowledge_mcp_server()
            servers["knowledge"] = knowledge_server
            logger.info("知识库 MCP 服务器已注册")

        except Exception as e:
            logger.warning(f"知识库 MCP 服务器注册失败: {e}")

        try:
            # 代码分析 MCP
            code_server = create_code_analysis_mcp_server()
            servers["code-analysis"] = code_server
            logger.info("代码分析 MCP 服务器已注册")

        except Exception as e:
            logger.warning(f"代码分析 MCP 服务器注册失败: {e}")

        try:
            # 网络搜索 MCP
            search_server = create_web_search_mcp_server()
            servers["web-search"] = search_server
            logger.info("网络搜索 MCP 服务器已注册")

        except Exception as e:
            logger.warning(f"网络搜索 MCP 服务器注册失败: {e}")

        self._mcp_servers = servers
        return servers

    async def _setup_hooks(self) -> dict[str, list[HookMatcher]]:
        """设置 Hook 回调

        Returns:
            Hook 配置字典
        """
        from mind.tools.hooks import ToolHooks

        hook_manager = ToolHooks()

        hooks: dict[str, list[HookMatcher]] = {
            "PreToolUse": [
                HookMatcher(
                    matcher=None,  # 所有工具
                    hooks=[hook_manager.pre_tool_use],  # type: ignore[list-item]
                    timeout=self.config.hook_timeout,
                )
            ],
            "PostToolUse": [
                HookMatcher(
                    matcher=None,
                    hooks=[hook_manager.post_tool_use],  # type: ignore[list-item]
                    timeout=self.config.hook_timeout,
                )
            ],
        }

        logger.info("Hook 回调已注册")
        return hooks

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
            工具返回结果
        """
        if not self._initialized:
            raise RuntimeError("SDK 工具管理器未初始化")

        try:
            # 构建查询提示
            prompt = f"""你是 {agent_name}。

当前对话主题：{self._extract_topic(messages)}

请使用工具回答以下问题：
{question}

可用的 MCP 工具：
- knowledge: 搜索对话历史
- code-analysis: 分析代码库
- web-search: 网络搜索
"""

            # 使用 SDK 客户端查询
            await self._client.query(prompt)

            # 收集响应
            response_parts = []
            from claude_agent_sdk.types import AssistantMessage, TextBlock

            async for msg in self._client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            response_parts.append(block.text)

            result = "".join(response_parts)

            # 记录统计
            self._tool_usage_stats["total_queries"] = (
                self._tool_usage_stats.get("total_queries", 0) + 1
            )

            # 返回结果（空字符串也返回，None 仅在真正的错误时返回）
            return result if result is not None else None

        except Exception as e:
            logger.error(f"SDK 查询失败: {e}")
            raise

    def _extract_topic(self, messages: list[MessageParam]) -> str:
        """从消息中提取主题

        Args:
            messages: 消息列表

        Returns:
            主题字符串
        """
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    # 提取第一行作为主题
                    lines = content.strip().split("\n")
                    return lines[0][:100]
        return "未知主题"

    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            try:
                await self._client.disconnect()
                logger.info("SDK 客户端已断开连接")
            except Exception as e:
                logger.error(f"SDK 清理失败: {e}")
            finally:
                self._client = None

        self._initialized = False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "mcp_servers": list(self._mcp_servers.keys()),
            "tool_usage": self._tool_usage_stats.copy(),
            "initialized": self._initialized,
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
