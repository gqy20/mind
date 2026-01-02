"""
Unit tests for SDKToolManager

测试 SDK 工具管理器的：
- 初始化逻辑
- MCP 服务器设置
- Hook 配置
- 工具查询功能
- 错误处理和降级
- 资源清理
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from mind.tools.sdk_tool_manager import SDKToolConfig, SDKToolManager


class TestSDKToolConfig:
    """测试 SDKToolConfig 配置类"""

    def test_config_defaults(self):
        """测试：默认配置值"""
        # Arrange & Act
        config = SDKToolConfig()

        # Assert
        assert config.enable_mcp is True
        assert config.tool_permissions == {}
        assert config.hook_timeout == 30.0
        assert config.max_budget_usd is None
        assert config.enable_hooks is True

    def test_config_with_custom_values(self):
        """测试：自定义配置值"""
        # Arrange & Act
        config = SDKToolConfig(
            enable_mcp=False,
            tool_permissions={"Bash": "deny"},
            hook_timeout=60.0,
            max_budget_usd=0.5,
            enable_hooks=False,
        )

        # Assert
        assert config.enable_mcp is False
        assert config.tool_permissions["Bash"] == "deny"
        assert config.hook_timeout == 60.0
        assert config.max_budget_usd == 0.5
        assert config.enable_hooks is False


class TestSDKToolManagerInitialization:
    """测试 SDKToolManager 初始化"""

    @pytest.fixture
    def mock_config(self):
        """创建测试配置（禁用 MCP 以避免依赖）"""
        return SDKToolConfig(
            enable_mcp=False,  # 禁用 MCP 简化测试
            enable_hooks=False,
        )

    @pytest.fixture
    def manager(self, mock_config):
        """创建管理器实例"""
        return SDKToolManager(config=mock_config)

    def test_initialization_state(self, manager):
        """测试：初始化状态"""
        # Assert
        assert manager._client is None
        assert manager._mcp_servers == {}
        assert manager._tool_usage_stats == {}
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_without_mcp_or_hooks(self, manager):
        """测试：不使用 MCP 和 Hooks 的初始化"""
        # Arrange
        assert manager._initialized is False

        # Mock SDK 客户端
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            await manager.initialize()

            # Assert
            assert manager._initialized is True
            assert manager._client is not None
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, manager):
        """测试：多次初始化不会重复创建客户端"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            await manager.initialize()
            first_client = manager._client

            # Act
            await manager.initialize()

            # Assert
            assert manager._client is first_client
            assert mock_client.connect.call_count == 1  # 只调用一次

    @pytest.mark.asyncio
    async def test_initialize_with_sdk_import_error(self, manager):
        """测试：SDK 未安装时抛出错误"""
        # Arrange
        assert manager._initialized is False

        # Mock SDK 导入失败
        error_msg = "No module named 'claude_agent_sdk'"
        with patch(
            "claude_agent_sdk.ClaudeSDKClient",
            side_effect=ImportError(error_msg),
        ):
            # Act & Assert
            with pytest.raises(RuntimeError, match="Claude Agent SDK 未安装"):
                await manager.initialize()

    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self, manager):
        """测试：清理释放资源"""
        # Arrange
        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            await manager.initialize()
            assert manager._initialized is True

            # Act
            await manager.cleanup()

            # Assert
            assert manager._initialized is False
            assert manager._client is None
            mock_client.disconnect.assert_called_once()


class TestSDKToolManagerQueryTool:
    """测试 SDKToolManager 工具查询功能"""

    @pytest_asyncio.fixture()
    async def initialized_manager(self):
        """创建已初始化的管理器"""
        config = SDKToolConfig(enable_mcp=False, enable_hooks=False)
        manager = SDKToolManager(config=config)

        # Mock SDK 客户端
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.query = AsyncMock()

        # Mock receive_response 返回模拟数据
        async def mock_receive():
            from claude_agent_sdk.types import AssistantMessage, TextBlock

            msg = AssistantMessage(
                content=[TextBlock(text="模拟工具结果")],
                model="claude-sonnet-4",
            )
            yield msg

            # ResultMessage 标记结束
            from claude_agent_sdk.types import ResultMessage

            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test",
            )

        mock_client.receive_response = mock_receive

        # Mock SDK 导入路径
        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            await manager.initialize()
            yield manager

    @pytest.mark.asyncio
    async def test_query_tool_not_initialized(self):
        """测试：未初始化时调用 query_tool 抛出错误"""
        # Arrange
        manager = SDKToolManager(config=SDKToolConfig())

        # Act & Assert
        with pytest.raises(RuntimeError, match="SDK 工具管理器未初始化"):
            await manager.query_tool("测试问题", [], "Agent A")

    @pytest.mark.asyncio
    async def test_query_tool_sends_query_and_returns_result(self, initialized_manager):
        """测试：query_tool 发送查询并返回结果"""
        # Arrange
        manager = initialized_manager
        messages = [{"role": "user", "content": "测试消息"}]

        # Act
        result = await manager.query_tool("分析对话", messages, "Agent A")

        # Assert
        assert result is not None
        assert "模拟工具结果" in result
        assert manager._tool_usage_stats["total_queries"] == 1

    @pytest.mark.asyncio
    async def test_query_tool_handles_empty_response(self, initialized_manager):
        """测试：处理空响应"""
        # Arrange
        manager = initialized_manager

        # Mock receive_response 返回空内容
        async def mock_receive_empty():
            from claude_agent_sdk.types import (
                AssistantMessage,
                ResultMessage,
                TextBlock,
            )

            yield AssistantMessage(
                content=[TextBlock(text="")],
                model="claude-sonnet-4",
            )
            yield ResultMessage(
                subtype="result",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test",
            )

        manager._client.receive_response = mock_receive_empty

        # Act
        result = await manager.query_tool("测试", [], "Agent")

        # Assert
        assert result == ""  # 空字符串，不是 None

    @pytest.mark.asyncio
    async def test_query_tool_increments_stats(self, initialized_manager):
        """测试：查询增加统计计数"""
        # Arrange
        manager = initialized_manager
        manager._tool_usage_stats = {"total_queries": 5}

        # Act
        await manager.query_tool("测试", [], "Agent")

        # Assert
        assert manager._tool_usage_stats["total_queries"] == 6


class TestSDKToolManagerMCPServers:
    """测试 MCP 服务器设置"""

    @pytest.mark.asyncio
    async def test_setup_mcp_servers_when_enabled(self):
        """测试：启用 MCP 时设置服务器"""
        # Arrange
        config = SDKToolConfig(enable_mcp=True, enable_hooks=False)
        manager = SDKToolManager(config=config)

        # Mock SDK 客户端
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            await manager.initialize()

            # Assert
            assert manager._mcp_servers is not None
            # 注意：实际的服务器数量取决于 MCP 模块的实现
            # 这里只验证方法被调用
            assert isinstance(manager._mcp_servers, dict)

    @pytest.mark.asyncio
    async def test_setup_mcp_servers_disabled(self):
        """测试：禁用 MCP 时不设置服务器"""
        # Arrange
        config = SDKToolConfig(enable_mcp=False, enable_hooks=False)
        manager = SDKToolManager(config=config)

        # Mock SDK 客户端
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            await manager.initialize()

            # Assert
            assert manager._mcp_servers == {}


class TestSDKToolManagerHooks:
    """测试 Hook 配置"""

    @pytest.mark.asyncio
    async def test_setup_hooks_when_enabled(self):
        """测试：启用 Hooks 时设置回调"""
        # Arrange
        config = SDKToolConfig(
            enable_mcp=False,
            enable_hooks=True,
            hook_timeout=45.0,
        )
        manager = SDKToolManager(config=config)

        # Mock SDK 客户端
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            await manager.initialize()

            # Assert - 验证 SDK 客户端被正确配置
            # (实际验证需要检查 SDK 的配置参数)
            assert manager._initialized is True


class TestSDKToolManagerStats:
    """测试统计功能"""

    def test_get_stats_returns_correct_info(self):
        """测试：get_stats 返回正确的统计信息"""
        # Arrange
        manager = SDKToolManager(config=SDKToolConfig())
        manager._mcp_servers = {"test-server": {}}
        manager._tool_usage_stats = {"total_queries": 10}
        manager._initialized = False

        # Act
        stats = manager.get_stats()

        # Assert
        assert "mcp_servers" in stats
        assert "tool_usage" in stats
        assert "initialized" in stats
        assert stats["mcp_servers"] == ["test-server"]
        assert stats["tool_usage"] == {"total_queries": 10}
        assert stats["initialized"] is False


class TestSDKToolManagerAsyncContext:
    """测试异步上下文管理器"""

    @pytest.mark.asyncio
    async def test_async_context_initializes_on_enter(self):
        """测试：进入上下文时自动初始化"""
        # Arrange
        config = SDKToolConfig(enable_mcp=False, enable_hooks=False)

        # Mock SDK 客户端
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            async with SDKToolManager(config=config) as manager:
                # Assert
                assert manager._initialized is True
                assert manager._client is not None

    @pytest.mark.asyncio
    async def test_async_context_cleans_up_on_exit(self):
        """测试：退出上下文时自动清理"""
        # Arrange
        config = SDKToolConfig(enable_mcp=False, enable_hooks=False)

        # Mock SDK 客户端
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act
            async with SDKToolManager(config=config) as manager:
                pass  # 仅用于测试上下文退出时的清理

            # Assert - 客户端已清理
            assert manager._client is None
            mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_cleans_up_on_exception(self):
        """测试：异常时仍会清理资源"""
        # Arrange
        config = SDKToolConfig(enable_mcp=False, enable_hooks=False)
        mock_client = AsyncMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()

        with patch("claude_agent_sdk.ClaudeSDKClient", return_value=mock_client):
            # Act & Assert
            with pytest.raises(ValueError):
                async with SDKToolManager(config=config) as manager:
                    assert manager._initialized is True
                    raise ValueError("测试异常")

            # 即使异常，也应该清理
            assert manager._client is None
            mock_client.disconnect.assert_called_once()
