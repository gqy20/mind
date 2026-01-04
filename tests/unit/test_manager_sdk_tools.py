"""
ConversationManager MCP 工具设置的单元测试

测试 ConversationManager._setup_sdk_tools 方法：
- 使用 MCPClientManager 获取 MCP 工具列表
- 将工具列表传递给智能体的 response_handler
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.config import HookConfig, MCPServerConfig, SettingsConfig, ToolsConfig


class TestSetupSDKTools:
    """测试 _setup_sdk_tools 方法"""

    @pytest.mark.asyncio
    async def test_setup_sdk_tools_with_mcp_servers(self):
        """测试：使用 MCP 服务器配置设置 SDK 工具"""
        # Arrange
        from mind.agents.agent import Agent
        from mind.manager import ConversationManager

        agent_a = Agent(
            name="Agent A", system_prompt="Prompt A", model="claude-3-5-sonnet-20241022"
        )
        agent_b = Agent(
            name="Agent B", system_prompt="Prompt B", model="claude-3-5-sonnet-20241022"
        )

        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
        )

        # Mock settings with MCP servers
        settings = SettingsConfig(
            tools=ToolsConfig(
                mcp_servers={
                    "knowledge": MCPServerConfig(
                        command="node",
                        args=["/path/to/knowledge.js"],
                    ),
                    "web-search": MCPServerConfig(
                        command="python",
                        args=["-m", "web_search"],
                    ),
                }
            )
        )

        # Mock MCP 工具返回值
        mock_tools = [
            {
                "name": "search_knowledge",
                "description": "Search knowledge base",
                "inputSchema": {},
            },
            {"name": "web_search", "description": "Search the web", "inputSchema": {}},
        ]

        # Mock MCPClientManager
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_all_tools = AsyncMock(return_value=mock_tools)
        mock_manager_instance.close = AsyncMock()

        # Act
        with patch(
            "mind.tools.mcp_client_manager.MCPClientManager",
            return_value=mock_manager_instance,
        ):
            await manager._setup_sdk_tools(settings)

        # Assert
        # 验证 MCP 工具被获取并传递给 response_handler
        assert agent_a.response_handler.mcp_tools == mock_tools
        assert agent_b.response_handler.mcp_tools == mock_tools
        assert len(mock_tools) == 2

    @pytest.mark.asyncio
    async def test_setup_sdk_tools_with_hooks(self):
        """测试：使用 Hook 配置（当前仅记录日志，不创建 SDK 客户端）"""
        # Arrange
        from mind.agents.agent import Agent
        from mind.manager import ConversationManager

        agent_a = Agent(
            name="Agent A", system_prompt="Prompt A", model="claude-3-5-sonnet-20241022"
        )
        agent_b = Agent(
            name="Agent B", system_prompt="Prompt B", model="claude-3-5-sonnet-20241022"
        )

        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
        )

        # Mock settings with hooks (no MCP servers)
        settings = SettingsConfig(
            tools=ToolsConfig(
                pre_tool_use=HookConfig(timeout=15.0, enabled=True),
                post_tool_use=HookConfig(timeout=20.0, enabled=True),
            )
        )

        # Act
        await manager._setup_sdk_tools(settings)

        # Assert
        # 没有 MCP 服务器时，mcp_tools 应该为空列表
        assert agent_a.response_handler.mcp_tools == []
        assert agent_b.response_handler.mcp_tools == []

    @pytest.mark.asyncio
    async def test_setup_sdk_tools_with_full_config(self):
        """测试：使用完整配置（MCP + Hooks）设置 SDK 工具"""
        # Arrange
        from mind.agents.agent import Agent
        from mind.manager import ConversationManager

        agent_a = Agent(
            name="Agent A", system_prompt="Prompt A", model="claude-3-5-sonnet-20241022"
        )
        agent_b = Agent(
            name="Agent B", system_prompt="Prompt B", model="claude-3-5-sonnet-20241022"
        )

        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
        )

        # Mock settings with full config
        settings = SettingsConfig(
            tools=ToolsConfig(
                mcp_servers={
                    "test": MCPServerConfig(
                        command="echo",
                        args=["test"],
                        env={"TEST": "1"},
                    )
                },
                pre_tool_use=HookConfig(timeout=30.0, enabled=True),
                post_tool_use=HookConfig(timeout=30.0, enabled=False),
            )
        )

        # Mock MCP 工具返回值
        mock_tools = [
            {"name": "test_tool", "description": "Test tool", "inputSchema": {}},
        ]

        # Mock MCPClientManager
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_all_tools = AsyncMock(return_value=mock_tools)
        mock_manager_instance.close = AsyncMock()

        # Act
        with patch(
            "mind.tools.mcp_client_manager.MCPClientManager",
            return_value=mock_manager_instance,
        ):
            await manager._setup_sdk_tools(settings)

        # Assert
        # 验证 MCP 工具被获取
        assert agent_a.response_handler.mcp_tools == mock_tools
        assert agent_b.response_handler.mcp_tools == mock_tools

    @pytest.mark.asyncio
    async def test_setup_sdk_tools_with_empty_config(self):
        """测试：空配置时不应设置 MCP 工具"""
        # Arrange
        from mind.agents.agent import Agent
        from mind.manager import ConversationManager

        agent_a = Agent(
            name="Agent A", system_prompt="Prompt A", model="claude-3-5-sonnet-20241022"
        )
        agent_b = Agent(
            name="Agent B", system_prompt="Prompt B", model="claude-3-5-sonnet-20241022"
        )

        manager = ConversationManager(
            agent_a=agent_a,
            agent_b=agent_b,
        )

        # Mock settings with empty config
        settings = SettingsConfig(tools=ToolsConfig())

        # Act
        await manager._setup_sdk_tools(settings)

        # Assert
        # 空配置时 mcp_tools 应该为空列表
        assert agent_a.response_handler.mcp_tools == []
        assert agent_b.response_handler.mcp_tools == []

    def test_mcp_config_to_sdk_format_conversion(self):
        """测试：MCP 配置转换为 SDK 格式"""
        # Arrange
        config = MCPServerConfig(
            command="python",
            args=["-m", "server"],
            env={"DEBUG": "true"},
        )

        # Act
        sdk_format = {
            "command": config.command,
            "args": config.args,
            "env": config.env,
        }

        # Assert
        assert sdk_format == {
            "command": "python",
            "args": ["-m", "server"],
            "env": {"DEBUG": "true"},
        }

    def test_multiple_mcp_servers_to_sdk_format(self):
        """测试：多个 MCP 服务器配置转换为 SDK 格式"""
        # Arrange
        tools_config = ToolsConfig(
            mcp_servers={
                "server1": MCPServerConfig(command="cmd1"),
                "server2": MCPServerConfig(command="cmd2", args=["arg"]),
            }
        )

        # Act
        sdk_format = {}
        for name, server_config in tools_config.mcp_servers.items():
            sdk_format[name] = {
                "command": server_config.command,
                "args": server_config.args,
                "env": server_config.env,
            }

        # Assert
        assert sdk_format == {
            "server1": {"command": "cmd1", "args": [], "env": {}},
            "server2": {"command": "cmd2", "args": ["arg"], "env": {}},
        }
