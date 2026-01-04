"""
ConversationManager SDK 工具设置的单元测试

测试 ConversationManager._setup_sdk_tools 方法：
- 将 MCP 服务器配置转换为 SDK 格式
- 构建 Hooks 配置
- 使用 SDK 原生配置创建客户端
"""

from unittest.mock import AsyncMock, MagicMock, patch

from mind.config import HookConfig, MCPServerConfig, SettingsConfig, ToolsConfig


class TestSetupSDKTools:
    """测试 _setup_sdk_tools 方法"""

    def test_setup_sdk_tools_with_mcp_servers(self):
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

        # Mock SDK client (mock in the __init__ scope where it's imported)
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()

        # Act
        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            with patch("claude_agent_sdk.ClaudeAgentOptions") as mock_options:
                manager._setup_sdk_tools(settings)

                # Assert
                # 验证 ClaudeAgentOptions 被调用，且包含 MCP 服务器配置
                assert mock_options.called
                call_kwargs = mock_options.call_args[1]
                mcp_servers_arg = call_kwargs.get("mcp_servers")

                # 验证 MCP 服务器配置
                assert mcp_servers_arg is not None
                assert "knowledge" in mcp_servers_arg
                assert "web-search" in mcp_servers_arg
                assert mcp_servers_arg["knowledge"]["command"] == "node"
                assert mcp_servers_arg["knowledge"]["args"] == ["/path/to/knowledge.js"]
                assert mcp_servers_arg["web-search"]["command"] == "python"
                assert mcp_servers_arg["web-search"]["args"] == ["-m", "web_search"]

    def test_setup_sdk_tools_with_hooks(self):
        """测试：使用 Hook 配置设置 SDK 工具"""
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

        # Mock settings with hooks
        settings = SettingsConfig(
            tools=ToolsConfig(
                pre_tool_use=HookConfig(timeout=15.0, enabled=True),
                post_tool_use=HookConfig(timeout=20.0, enabled=True),
            )
        )

        # Act
        with patch("claude_agent_sdk.ClaudeSDKClient"):
            with patch("claude_agent_sdk.ClaudeAgentOptions") as mock_options:
                manager._setup_sdk_tools(settings)

                # Assert
                assert mock_options.called
                call_kwargs = mock_options.call_args[1]
                hooks_arg = call_kwargs.get("hooks")

                # 验证 Hook 配置
                assert hooks_arg is not None
                assert "PreToolUse" in hooks_arg
                assert "PostToolUse" in hooks_arg

    def test_setup_sdk_tools_with_full_config(self):
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

        # Act
        with patch("claude_agent_sdk.ClaudeSDKClient"):
            with patch("claude_agent_sdk.ClaudeAgentOptions") as mock_options:
                manager._setup_sdk_tools(settings)

                # Assert
                assert mock_options.called

    def test_setup_sdk_tools_with_empty_config(self):
        """测试：空配置时不应创建 SDK 客户端"""
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
        with patch("claude_agent_sdk.ClaudeSDKClient") as mock_sdk:
            manager._setup_sdk_tools(settings)

            # Assert
            # 空配置时不应该调用 SDK
            assert not mock_sdk.called
            assert manager._sdk_client is None

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
