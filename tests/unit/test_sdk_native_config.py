"""
SDK 原生配置模块的单元测试

测试使用 SDK 原生的 mcp_servers 和 hooks 配置：
- MCPServerConfig 配置模型
- HookConfig 配置模型
- ToolsConfig 扩展（包含 MCP 和 Hooks）
- 从 YAML 加载 SDK 配置
- 配置转换为 SDK 格式
"""

import pytest
import yaml
from pydantic import ValidationError

from mind.config import (
    HookConfig,
    MCPServerConfig,
    SettingsConfig,
    ToolsConfig,
)


class TestMCPServerConfig:
    """测试 MCP 服务器配置模型"""

    def test_mcp_server_config_valid_with_command_only(self):
        """测试：仅包含命令的有效配置"""
        # Arrange & Act
        config = MCPServerConfig(command="node")

        # Assert
        assert config.command == "node"
        assert config.args == []
        assert config.env == {}

    def test_mcp_server_config_valid_with_args(self):
        """测试：包含命令和参数的有效配置"""
        # Arrange & Act
        config = MCPServerConfig(command="python", args=["-m", "web_search_server"])

        # Assert
        assert config.command == "python"
        assert config.args == ["-m", "web_search_server"]
        assert config.env == {}

    def test_mcp_server_config_valid_with_env(self):
        """测试：包含环境变量的有效配置"""
        # Arrange & Act
        config = MCPServerConfig(
            command="node",
            args=["/path/to/server.js"],
            env={"NODE_ENV": "production", "API_KEY": "test_key"},
        )

        # Assert
        assert config.command == "node"
        assert config.args == ["/path/to/server.js"]
        assert config.env == {"NODE_ENV": "production", "API_KEY": "test_key"}

    def test_mcp_server_config_missing_command(self):
        """测试：缺少 command 字段应抛出 ValidationError"""
        # Act & Assert
        with pytest.raises(ValidationError, match="command"):
            MCPServerConfig(args=["-m", "server"])

    def test_mcp_server_config_to_sdk_format(self):
        """测试：转换为 SDK 格式字典"""
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


class TestHookConfig:
    """测试 Hook 配置模型"""

    def test_hook_config_valid_default_values(self):
        """测试：使用默认值的有效配置"""
        # Arrange & Act
        config = HookConfig()

        # Assert
        assert config.timeout == 30.0
        assert config.enabled is True

    def test_hook_config_valid_custom_values(self):
        """测试：自定义值的有效配置"""
        # Arrange & Act
        config = HookConfig(timeout=60.0, enabled=False)

        # Assert
        assert config.timeout == 60.0
        assert config.enabled is False

    def test_hook_config_timeout_zero(self):
        """测试：timeout 为 0 应该有效"""
        # Arrange & Act
        config = HookConfig(timeout=0.0, enabled=True)

        # Assert
        assert config.timeout == 0.0
        assert config.enabled is True

    def test_hook_config_negative_timeout(self):
        """测试：负数 timeout 应该有效（Pydantic 不会自动检查）"""
        # Arrange & Act
        config = HookConfig(timeout=-10.0)

        # Assert
        assert config.timeout == -10.0


class TestToolsConfig:
    """测试扩展的 ToolsConfig 模型"""

    def test_tools_config_default_values(self):
        """测试：使用默认值的 ToolsConfig"""
        # Arrange & Act
        config = ToolsConfig()

        # Assert
        assert config.tool_interval == 5
        assert config.enable_tools is True
        assert config.enable_search is True
        assert config.mcp_servers == {}
        assert config.pre_tool_use is None
        assert config.post_tool_use is None

    def test_tools_config_with_mcp_servers(self):
        """测试：包含 MCP 服务器配置"""
        # Arrange & Act
        config = ToolsConfig(
            mcp_servers={
                "knowledge": MCPServerConfig(
                    command="node", args=["/path/to/knowledge.js"]
                ),
                "web-search": MCPServerConfig(
                    command="python", args=["-m", "web_search"]
                ),
            }
        )

        # Assert
        assert len(config.mcp_servers) == 2
        assert "knowledge" in config.mcp_servers
        assert "web-search" in config.mcp_servers
        assert config.mcp_servers["knowledge"].command == "node"
        assert config.mcp_servers["web-search"].command == "python"

    def test_tools_config_with_hooks(self):
        """测试：包含 Hook 配置"""
        # Arrange & Act
        config = ToolsConfig(
            pre_tool_use=HookConfig(timeout=15.0),
            post_tool_use=HookConfig(timeout=20.0, enabled=False),
        )

        # Assert
        assert config.pre_tool_use is not None
        assert config.post_tool_use is not None
        assert config.pre_tool_use.timeout == 15.0
        assert config.pre_tool_use.enabled is True
        assert config.post_tool_use.timeout == 20.0
        assert config.post_tool_use.enabled is False

    def test_tools_config_full_configuration(self):
        """测试：完整的 ToolsConfig 配置"""
        # Arrange & Act
        config = ToolsConfig(
            tool_interval=10,
            enable_tools=False,
            enable_search=False,
            mcp_servers={
                "test": MCPServerConfig(
                    command="echo", args=["test"], env={"TEST": "1"}
                )
            },
            pre_tool_use=HookConfig(timeout=30.0),
            post_tool_use=HookConfig(timeout=30.0),
        )

        # Assert
        assert config.tool_interval == 10
        assert config.enable_tools is False
        assert config.enable_search is False
        assert len(config.mcp_servers) == 1
        assert config.mcp_servers["test"].command == "echo"
        assert config.pre_tool_use.timeout == 30.0
        assert config.post_tool_use.timeout == 30.0


class TestLoadSettingsWithSDKConfig:
    """测试从 YAML 加载 SDK 配置"""

    def test_load_settings_with_mcp_servers(self, tmp_path):
        """测试：从 YAML 加载包含 MCP 服务器配置"""
        # Arrange
        config_content = {
            "settings": {
                "tools": {
                    "tool_interval": 5,
                    "enable_tools": True,
                    "enable_search": True,
                    "mcp_servers": {
                        "knowledge": {
                            "command": "node",
                            "args": ["/path/to/knowledge.js"],
                        },
                        "web-search": {
                            "command": "python",
                            "args": ["-m", "web_search"],
                        },
                    },
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f, allow_unicode=True)

        # Act
        from mind.config import load_settings

        settings = load_settings(config_file)

        # Assert
        assert isinstance(settings, SettingsConfig)
        assert isinstance(settings.tools, ToolsConfig)
        assert len(settings.tools.mcp_servers) == 2
        assert "knowledge" in settings.tools.mcp_servers
        assert "web-search" in settings.tools.mcp_servers
        assert settings.tools.mcp_servers["knowledge"].command == "node"
        assert settings.tools.mcp_servers["knowledge"].args == ["/path/to/knowledge.js"]
        assert settings.tools.mcp_servers["web-search"].command == "python"

    def test_load_settings_with_hooks(self, tmp_path):
        """测试：从 YAML 加载包含 Hook 配置"""
        # Arrange
        config_content = {
            "settings": {
                "tools": {
                    "tool_interval": 5,
                    "enable_tools": True,
                    "enable_search": True,
                    "pre_tool_use": {
                        "timeout": 15.0,
                        "enabled": True,
                    },
                    "post_tool_use": {
                        "timeout": 20.0,
                        "enabled": False,
                    },
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f, allow_unicode=True)

        # Act
        from mind.config import load_settings

        settings = load_settings(config_file)

        # Assert
        assert isinstance(settings, SettingsConfig)
        assert isinstance(settings.tools, ToolsConfig)
        assert settings.tools.pre_tool_use is not None
        assert settings.tools.post_tool_use is not None
        assert settings.tools.pre_tool_use.timeout == 15.0
        assert settings.tools.pre_tool_use.enabled is True
        assert settings.tools.post_tool_use.timeout == 20.0
        assert settings.tools.post_tool_use.enabled is False

    def test_load_settings_with_full_sdk_config(self, tmp_path):
        """测试：从 YAML 加载完整的 SDK 配置"""
        # Arrange
        config_content = {
            "settings": {
                "tools": {
                    "tool_interval": 10,
                    "enable_tools": True,
                    "enable_search": True,
                    "mcp_servers": {
                        "knowledge": {
                            "command": "node",
                            "args": ["/path/to/knowledge.js"],
                            "env": {"NODE_ENV": "production"},
                        },
                    },
                    "pre_tool_use": {"timeout": 30.0, "enabled": True},
                    "post_tool_use": {"timeout": 30.0, "enabled": True},
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f, allow_unicode=True)

        # Act
        from mind.config import load_settings

        settings = load_settings(config_file)

        # Assert
        assert settings.tools.tool_interval == 10
        assert len(settings.tools.mcp_servers) == 1
        assert settings.tools.mcp_servers["knowledge"].command == "node"
        assert settings.tools.mcp_servers["knowledge"].env == {"NODE_ENV": "production"}
        assert settings.tools.pre_tool_use.timeout == 30.0
        assert settings.tools.post_tool_use.timeout == 30.0

    def test_load_settings_empty_mcp_servers(self, tmp_path):
        """测试：空的 MCP 服务器配置应返回空字典"""
        # Arrange
        config_content = {
            "settings": {
                "tools": {
                    "tool_interval": 5,
                    "enable_tools": True,
                    "enable_search": True,
                    "mcp_servers": {},
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f)

        # Act
        from mind.config import load_settings

        settings = load_settings(config_file)

        # Assert
        assert settings.tools.mcp_servers == {}

    def test_load_settings_no_mcp_servers(self, tmp_path):
        """测试：没有 mcp_servers 字段时应返回默认空字典"""
        # Arrange
        config_content = {
            "settings": {
                "tools": {
                    "tool_interval": 5,
                    "enable_tools": True,
                    "enable_search": True,
                }
            }
        }
        config_file = tmp_path / "prompts.yaml"
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_content, f)

        # Act
        from mind.config import load_settings

        settings = load_settings(config_file)

        # Assert
        assert settings.tools.mcp_servers == {}


class TestMCPConfigToSDKFormat:
    """测试配置转换为 SDK 格式"""

    def test_single_mcp_server_to_sdk_format(self):
        """测试：单个 MCP 服务器转换为 SDK 格式"""
        # Arrange
        config = MCPServerConfig(
            command="python", args=["-m", "web_search"], env={"DEBUG": "1"}
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
            "args": ["-m", "web_search"],
            "env": {"DEBUG": "1"},
        }

    def test_multiple_mcp_servers_to_sdk_format(self):
        """测试：多个 MCP 服务器转换为 SDK 格式"""
        # Arrange
        config = ToolsConfig(
            mcp_servers={
                "server1": MCPServerConfig(command="cmd1"),
                "server2": MCPServerConfig(command="cmd2", args=["arg"]),
            }
        )

        # Act
        sdk_format = {}
        for name, server_config in config.mcp_servers.items():
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
