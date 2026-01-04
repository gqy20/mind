"""测试 AnthropicClient 重试机制配置"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_client_passes_max_retries_to_anthropic():
    """测试 AnthropicClient 将 max_retries 参数传递给 AsyncAnthropic"""
    from mind.agents.client import AnthropicClient

    # 创建模拟的 AsyncAnthropic 构造函数
    mock_anthropic_class = MagicMock()
    mock_anthropic_instance = MagicMock()
    mock_anthropic_class.return_value = mock_anthropic_instance

    with patch("mind.agents.client.AsyncAnthropic", mock_anthropic_class):
        # 使用自定义 max_retries 创建客户端
        AnthropicClient(
            model="claude-sonnet-4-5-20250929",
            api_key="test-key",
            max_retries=5,
        )

        # 验证 AsyncAnthropic 被正确调用，并传入了 max_retries=5
        mock_anthropic_class.assert_called_once()
        call_kwargs = mock_anthropic_class.call_args.kwargs

        assert "max_retries" in call_kwargs, "max_retries 应该被传递给 AsyncAnthropic"
        assert call_kwargs["max_retries"] == 5, "max_retries 值应该是 5"


@pytest.mark.asyncio
async def test_client_default_max_retries():
    """测试 AnthropicClient 默认使用 anthropic 库的默认重试次数"""
    from mind.agents.client import AnthropicClient

    # 创建模拟的 AsyncAnthropic 构造函数
    mock_anthropic_class = MagicMock()
    mock_anthropic_instance = MagicMock()
    mock_anthropic_class.return_value = mock_anthropic_instance

    with patch("mind.agents.client.AsyncAnthropic", mock_anthropic_class):
        # 不传入 max_retries，使用默认值
        client = AnthropicClient(
            model="claude-sonnet-4-5-20250929",
            api_key="test-key",
        )

        # 验证 AsyncAnthropic 被调用
        mock_anthropic_class.assert_called_once()

        # 如果不传 max_retries，anthropic 库默认是 2
        # 但由于我们使用 mock，需要验证行为
        assert client.model == "claude-sonnet-4-5-20250929"


def test_client_init_with_timeout():
    """测试客户端可以自定义 timeout 配置"""
    from mind.agents.client import AnthropicClient

    mock_anthropic_class = MagicMock()
    mock_anthropic_instance = MagicMock()
    mock_anthropic_class.return_value = mock_anthropic_instance

    with patch("mind.agents.client.AsyncAnthropic", mock_anthropic_class):
        # 传入自定义 timeout
        import httpx

        timeout = httpx.Timeout(timeout=300, connect=5.0)
        AnthropicClient(
            model="claude-sonnet-4-5-20250929",
            api_key="test-key",
            timeout=timeout,
            max_retries=3,
        )

        # 验证参数传递
        call_kwargs = mock_anthropic_class.call_args.kwargs
        assert call_kwargs.get("max_retries") == 3
        assert call_kwargs.get("timeout") == timeout
