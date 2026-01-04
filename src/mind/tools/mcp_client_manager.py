"""MCP 客户端管理器 - 管理与 MCP 服务器的连接和工具获取

使用 mcp 库连接到 MCP 服务器并获取可用工具列表。
"""

from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from mind.logger import get_logger

logger = get_logger("mind.mcp_client_manager")


class MCPClientManager:
    """MCP 客户端管理器"""

    def __init__(self):
        """初始化 MCP 客户端管理器"""
        self._sessions: dict[str, Any] = {}
        self._tools_cache: dict[str, list[dict]] = {}
        # 存储服务器配置，用于执行工具时重新连接
        self._server_configs: dict[str, dict] = {}
        # 工具名到服务器名的映射
        self._tool_to_server: dict[str, str] = {}

    async def get_tools(self, server_name: str, server_config: dict) -> list[dict]:
        """获取 MCP 服务器的工具列表

        Args:
            server_name: 服务器名称
            server_config: 服务器配置（command, args, env）

        Returns:
            工具列表
        """
        # 检查缓存
        if server_name in self._tools_cache:
            return self._tools_cache[server_name]

        # 存储服务器配置
        self._server_configs[server_name] = server_config

        try:
            # 创建服务器参数
            params = StdioServerParameters(
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", None),
            )

            # 连接到服务器（ClientSession 也需要作为上下文管理器）
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # 获取工具列表
                    tools_response = await session.list_tools()
                    tools = []
                    for tool in tools_response.tools:
                        tool_dict = {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                        }
                        tools.append(tool_dict)
                        # 建立工具名到服务器名的映射
                        self._tool_to_server[tool.name] = server_name

                    # 缓存结果
                    self._tools_cache[server_name] = tools
                    logger.info(f"从 {server_name} 获取了 {len(tools)} 个工具")
                    return tools

        except Exception as e:
            logger.error(f"从 {server_name} 获取工具失败: {e}")
            return []

    async def get_all_tools(self, mcp_servers: dict) -> list[dict]:
        """获取所有 MCP 服务器的工具

        Args:
            mcp_servers: MCP 服务器配置字典（MCPServerConfig 对象）

        Returns:
            所有工具的列表
        """
        all_tools = []
        for server_name, server_config in mcp_servers.items():
            config_dict = {
                "command": server_config.command,
                "args": server_config.args,
                "env": dict(server_config.env) if server_config.env else None,
            }
            tools = await self.get_tools(server_name, config_dict)
            all_tools.extend(tools)

        return all_tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any | None:
        """调用 MCP 工具

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果，失败返回 None
        """
        # 查找工具所属的服务器
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            logger.error(f"未找到工具 {tool_name} 对应的服务器")
            return None

        server_config = self._server_configs.get(server_name)
        if not server_config:
            logger.error(f"未找到服务器 {server_name} 的配置")
            return None

        try:
            # 创建服务器参数
            params = StdioServerParameters(
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", None),
            )

            # 连接到服务器并调用工具
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    # 调用工具
                    result = await session.call_tool(tool_name, arguments)

                    # 提取结果内容
                    if hasattr(result, "content"):
                        # 处理 TextContent 和其他内容类型
                        content_parts = []
                        for content in result.content:
                            if hasattr(content, "text"):
                                content_parts.append(content.text)
                            else:
                                # 对于其他类型（如 ImageContent），转换为字符串
                                content_parts.append(str(content))
                        return "\n".join(content_parts)
                    else:
                        return str(result)

        except Exception as e:
            logger.error(f"调用工具 {tool_name} 失败: {e}")
            return None

    async def close(self):
        """关闭所有连接"""
        for session in self._sessions.values():
            try:
                if hasattr(session, "close"):
                    await session.close()
            except Exception as e:
                logger.warning(f"关闭会话失败: {e}")
        self._sessions.clear()
        self._tools_cache.clear()
