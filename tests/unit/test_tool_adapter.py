"""
Unit tests for ToolAdapter

测试工具适配器的：
- 初始化逻辑
- SDK/Fallback 切换
- 降级处理
- 统计功能
"""

from unittest.mock import AsyncMock

import pytest

from mind.tools.adapters.tool_adapter import (
    ToolAdapter,
    ToolAdapterConfig,
    create_tool_adapter,
)


class TestToolAdapterConfig:
    """测试 ToolAdapterConfig 配置类"""

    def test_config_defaults_to_not_use_sdk(self):
        """测试：默认配置不使用 SDK"""
        # Arrange & Act
        config = ToolAdapterConfig()

        # Assert
        assert config.use_sdk is False
        assert config.enable_mcp is True
        assert config.fallback_on_error is True
        assert config.max_retries == 2

    def test_config_from_env_var(self, monkeypatch):
        """测试：从环境变量读取配置"""
        # Arrange
        monkeypatch.setenv("MIND_USE_SDK_TOOLS", "true")
        monkeypatch.setenv("MIND_ENABLE_MCP", "false")

        # Act
        config = ToolAdapterConfig()

        # Assert
        assert config.use_sdk is True
        assert config.enable_mcp is False


class TestToolAdapter:
    """测试 ToolAdapter 核心功能"""

    @pytest.fixture
    def mock_config(self):
        """创建测试配置"""
        return ToolAdapterConfig(
            use_sdk=False,  # 先不使用 SDK，测试降级
            fallback_on_error=True,
        )

    @pytest.fixture
    def adapter(self, mock_config):
        """创建适配器实例"""
        return ToolAdapter(config=mock_config)

    def test_initialization_without_sdk(self, adapter):
        """测试：不使用 SDK 时的初始化"""
        # Assert
        assert adapter.config.use_sdk is False
        assert adapter._sdk_manager is None
        assert adapter._fallback_agent is None

    @pytest.mark.asyncio
    async def test_initialize_creates_fallback_agent(self, adapter):
        """测试：初始化创建降级代理"""
        # Arrange
        assert adapter._fallback_agent is None

        # Act
        await adapter.initialize()

        # Assert
        assert adapter._fallback_agent is not None
        assert "ToolAgent" in str(type(adapter._fallback_agent))

    @pytest.mark.asyncio
    async def test_fallback_enabled_when_sdk_not_available(self):
        """测试：SDK 不可用时启用降级代理"""
        # Arrange
        config = ToolAdapterConfig(use_sdk=False, fallback_on_error=True)
        adapter = ToolAdapter(config=config)

        # Act
        await adapter.initialize()

        # Assert
        assert adapter._sdk_manager is None
        assert adapter._fallback_agent is not None
        assert adapter._fallback_agent is not None

        # Cleanup
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_query_tool_uses_fallback_when_sdk_unavailable(self, adapter):
        """测试：SDK 不可用时使用降级代理"""
        # Arrange
        await adapter.initialize()
        from anthropic.types import MessageParam

        messages: list[MessageParam] = [{"role": "user", "content": "测试消息"}]

        # Mock 降级代理响应
        adapter._fallback_agent.query_tool = AsyncMock(return_value="降级结果")

        # Act
        result = await adapter.query_tool(
            question="测试问题",
            messages=messages,
            agent_name="测试智能体",
        )

        # Assert
        assert result == "降级结果"
        adapter._fallback_agent.query_tool.assert_called_once()
        assert adapter._stats["fallback_calls"] == 1
        assert adapter._stats["sdk_calls"] == 0

    @pytest.mark.asyncio
    async def test_query_tool_returns_none_on_both_failures(self, adapter):
        """测试：SDK 和降级都失败时返回 None"""
        # Arrange
        await adapter.initialize()

        # Mock 降级代理失败
        error = Exception("测试错误")
        adapter._fallback_agent.query_tool = AsyncMock(side_effect=error)

        # Act
        result = await adapter.query_tool(
            question="测试问题",
            messages=[],
            agent_name="测试智能体",
        )

        # Assert
        assert result is None
        assert adapter._stats["errors"] == 1

    def test_get_stats_returns_usage_statistics(self, adapter):
        """测试：获取统计信息"""
        # Act
        stats = adapter.get_stats()

        # Assert
        assert "sdk_calls" in stats
        assert "fallback_calls" in stats
        assert "errors" in stats
        assert stats["sdk_calls"] == 0
        assert stats["fallback_calls"] == 0

    def test_reset_stats_clears_counters(self, adapter):
        """测试：重置统计信息"""
        # Arrange
        adapter._stats = {"sdk_calls": 5, "fallback_calls": 3, "errors": 1}

        # Act
        adapter.reset_stats()

        # Assert
        assert adapter._stats["sdk_calls"] == 0
        assert adapter._stats["fallback_calls"] == 0
        assert adapter._stats["errors"] == 0


class TestToolAdapterAsyncContext:
    """测试 ToolAdapter 异步上下文管理器"""

    @pytest.mark.asyncio
    async def test_async_context_manager_initializes_on_enter(self):
        """测试：进入上下文时自动初始化"""
        # Arrange
        adapter = ToolAdapter(ToolAdapterConfig(use_sdk=False))

        # Act
        async with adapter as ctx:
            # Assert
            assert ctx is adapter
            assert adapter._fallback_agent is not None

    @pytest.mark.asyncio
    async def test_async_context_manager_cleans_up_on_exit(self):
        """测试：退出上下文时自动清理"""
        # Arrange & Act
        async with ToolAdapter(ToolAdapterConfig(use_sdk=False)):
            pass  # 仅测试清理不抛异常

        # Assert - 如果没有异常，说明清理成功
        assert True


class TestCreateToolAdapter:
    """测试 create_tool_adapter 便捷函数"""

    @pytest.mark.asyncio
    async def test_creates_and_initializes_adapter(self):
        """测试：创建并初始化适配器"""
        # Act
        adapter = await create_tool_adapter(use_sdk=False, enable_mcp=False)

        # Assert
        assert isinstance(adapter, ToolAdapter)
        assert adapter._fallback_agent is not None

        # Cleanup
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_respects_use_sdk_parameter(self):
        """测试：尊重 use_sdk 参数"""
        # Act
        adapter = await create_tool_adapter(use_sdk=False)

        # Assert
        assert adapter.config.use_sdk is False

        # Cleanup
        await adapter.cleanup()
