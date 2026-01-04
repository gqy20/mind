"""
MCP 集成测试 - 验证 SDK 工具正确传递到 API 调用链路

测试目标：
1. _setup_sdk_tools 被调用
2. sdk_client 传递给 Agent
3. MCP 工具合并到工具 schema
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.config import get_default_config_path, load_all_configs


class TestSetupSDKToolsCalled:
    """测试 _setup_sdk_tools 被调用"""

    @patch("mind.cli.check_config")
    @patch("mind.agents.AgentFactory")
    @patch("mind.cli.ConversationManager")
    @patch("mind.cli.input")
    @pytest.mark.asyncio
    async def test_main_calls_setup_sdk_tools(
        self, mock_input, mock_manager, mock_factory, mock_check_config
    ):
        """测试：main() 创建 manager 后应调用 _setup_sdk_tools(settings)"""
        # Arrange
        mock_check_config.return_value = True
        mock_input.return_value = "测试主题"

        # Mock AgentFactory 返回值
        mock_agent_instance = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_instance.create_conversation_agents.return_value = {
            "supporter": mock_agent_instance,
            "challenger": mock_agent_instance,
        }
        mock_factory.return_value = mock_factory_instance

        # Mock ConversationManager 返回值
        mock_manager_instance = AsyncMock()
        mock_manager.return_value = mock_manager_instance

        # Act
        from mind.cli import main

        await main()

        # Assert
        # 1. ConversationManager 应该被创建
        assert mock_manager.call_count == 1

        # 2. _setup_sdk_tools 应该被调用
        # 获取创建的 manager 实例
        created_manager = mock_manager.return_value

        # 验证 _setup_sdk_tools 是否被调用
        # （当前会失败，因为 cli.py 没有调用这个方法）
        assert hasattr(created_manager, "_setup_sdk_tools"), (
            "ConversationManager 应该有 _setup_sdk_tools 方法"
        )

        # 验证 _setup_sdk_tools 被调用
        # 注意：这个断言当前会失败，因为方法没有被调用
        setup_method = getattr(created_manager, "_setup_sdk_tools", None)
        if setup_method:
            # 检查是否被调用（使用 mock）
            if hasattr(setup_method, "assert_called"):
                setup_method.assert_called_once()
            else:
                # 如果不是 mock，我们需要另一种方式验证
                # 这里我们先让测试失败，证明需要实现
                pytest.fail(
                    "_setup_sdk_tools 应该被调用，但当前没有验证方式。"
                    "需要将 ConversationManager._setup_sdk_tools 改为可 mock 的形式。"
                )


class TestMCPConfigurationLoaded:
    """测试 MCP 配置正确加载"""

    def test_mcp_config_loaded_from_yaml(self):
        """测试：从 YAML 加载的配置应包含 MCP 服务器"""
        # Arrange & Act
        config_path = get_default_config_path()
        _, settings = load_all_configs(config_path)

        # Assert
        # 当前应该有一个 article-mcp 服务器配置
        assert "article-mcp" in settings.tools.mcp_servers
        mcp_config = settings.tools.mcp_servers["article-mcp"]
        assert mcp_config.command == "uvx"
        assert mcp_config.args == ["article-mcp"]
        # 环境变量应该被展开
        assert "EASYSCHOLAR_SECRET_KEY" in mcp_config.env


class TestSDKClientPassedToAgent:
    """测试 MCP 工具传递给智能体"""

    def test_agent_response_handler_accepts_mcp_tools(self):
        """测试：Agent 的 ResponseHandler 应该能够接收 mcp_tools 参数"""
        # Arrange
        from mind.agents import Agent

        mcp_tools = [
            {
                "name": "search_article",
                "description": "搜索学术文章",
                "inputSchema": {"type": "object"},
            }
        ]

        # Act & Assert
        agent = Agent(
            name="测试智能体",
            system_prompt="你是一个测试智能体",
        )

        # 更新 response_handler 的 mcp_tools
        agent.response_handler.mcp_tools = mcp_tools

        # 验证 mcp_tools 被存储
        assert agent.response_handler.mcp_tools == mcp_tools


class TestMCPToolsInSchema:
    """测试 MCP 工具合并到工具 schema"""

    def test_get_tools_schema_includes_mcp_tools(self):
        """测试：工具 schema 应包含 MCP 工具"""
        # Arrange
        from mind.agents.response import _get_tools_schema

        mcp_tools = [
            {
                "name": "search_article",
                "description": "搜索学术文章",
                "inputSchema": {"type": "object", "properties": {}},
            }
        ]

        # Act
        tools_schema = _get_tools_schema(mcp_tools)

        # Assert
        # ToolParam 返回字典格式，使用字典访问
        # 应该包含内置的 search_web 工具
        search_web_found = any(t["name"] == "search_web" for t in tools_schema)
        assert search_web_found, "应该包含 search_web 工具"

        # 应该包含 MCP 工具
        article_found = any(t["name"] == "search_article" for t in tools_schema)
        assert article_found, "应该包含 search_article MCP 工具"

        # 验证工具数量：1 个内置 + 1 个 MCP = 2 个
        assert len(tools_schema) == 2
