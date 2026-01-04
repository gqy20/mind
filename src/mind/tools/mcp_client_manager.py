"""MCP 客户端管理器 - 管理与 MCP 服务器的连接和工具获取

使用 mcp 库连接到 MCP 服务器并获取可用工具列表。
"""

from typing import Any

from mcp.client.stdio import StdioServerParameters, stdio_client

from mind.logger import get_logger

logger = get_logger("mind.mcp_client_manager")


class MCPClientManager:
    """MCP 客户端管理器"""

    def __init__(self):
        """初始化 MCP 客户端管理器"""
        self._sessions: dict[str, Any] = {}
        self._tools_cache: dict[str, list[dict]] = {}

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

        try:
            # 创建服务器参数
            params = StdioServerParameters(
                command=server_config.get("command", ""),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
            )

            # 连接到服务器
            async with stdio_client(params) as session:
                # 初始化会话
                await session.initialize()

                # 获取工具列表
                tools_response = await session.list_tools()
                tools = []
                for tool in tools_response.tools:
                    tools.append(
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema,
                        }
                    )

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
            mcp_servers: MCP 服务器配置字典

        Returns:
            所有工具的列表
        """
        all_tools = []
        for server_name, server_config in mcp_servers.items():
            config_dict = {
                "command": server_config.command,
                "args": server_config.args,
                "env": server_config.env,
            }
            tools = await self.get_tools(server_name, config_dict)
            all_tools.extend(tools)

        return all_tools

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
