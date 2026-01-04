"""测试扩展的内部思考标签过滤功能

验证常见的 AI 内部思考标签都被正确过滤。
"""

import pytest


def test_default_stop_tokens_includes_common_internal_tags():
    """测试默认 stop_tokens 包含常见的内部思考标签"""
    from mind.config import SettingsConfig

    settings = SettingsConfig()

    # 验证包含基本的 thinking 标签
    assert "<thinking>" in settings.stop_tokens
    assert "</thinking>" in settings.stop_tokens

    # 验证包含 reflection 标签
    assert "<reflection>" in settings.stop_tokens
    assert "</reflection>" in settings.stop_tokens

    # 验证不超过 4 个（API 限制）
    assert len(settings.stop_tokens) <= 4, "stop_tokens 不能超过 4 个（API 限制）"


def test_stop_tokens_config_loads_from_yaml():
    """测试 stop_tokens 从 YAML 配置文件正确加载"""
    from mind.config import get_default_config_path, load_settings

    config_path = get_default_config_path()
    settings = load_settings(config_path)

    # 验证 stop_tokens 列表不为空
    assert settings.stop_tokens
    assert len(settings.stop_tokens) >= 2

    # 验证包含基本标签
    assert "<thinking>" in settings.stop_tokens
    assert "</thinking>" in settings.stop_tokens


def test_agent_receives_extended_stop_tokens():
    """测试 Agent 正确接收扩展的 stop_tokens"""
    from mind.agents.agent import Agent
    from mind.config import get_default_config_path, load_all_configs

    config_path = get_default_config_path()
    agent_configs, settings = load_all_configs(config_path)
    agent_config = agent_configs["supporter"]

    agent = Agent(
        name=agent_config.name,
        system_prompt=agent_config.system_prompt,
        model="claude-sonnet-4-5-20250929",
        settings=settings,
    )

    # 验证 agent 的 stop_tokens 与配置一致
    assert agent.stop_tokens == settings.stop_tokens
    assert len(agent.stop_tokens) >= 2


@pytest.mark.asyncio
async def test_stop_tokens_prevents_internal_tag_output():
    """测试 stop_tokens 防止内部标签输出到响应中"""
    from unittest.mock import AsyncMock, MagicMock, patch

    from mind.agents.client import AnthropicClient

    # 模拟响应事件（包含 thinking 标签）
    mock_events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "Hello"
    mock_events.append(text_event)

    # 创建模拟的流
    async def mock_iter():
        for event in mock_events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    # 注意：现在使用 beta.messages.stream 而不是 messages.stream
    mock_beta_messages = MagicMock()
    mock_beta_messages.stream = MagicMock(return_value=mock_stream)

    mock_anthropic = MagicMock()
    mock_anthropic.beta.messages = mock_beta_messages

    with patch("mind.agents.client.AsyncAnthropic", return_value=mock_anthropic):
        client = AnthropicClient(model="test-model", api_key="test-key")

        # 调用 stream，传入 stop_tokens
        stop_tokens = ["<thinking>", "</thinking>", "<reflection>", "</reflection>"]
        async for _ in client.stream(
            messages=[{"role": "user", "content": "test"}],
            system="test system",
            stop_tokens=stop_tokens,
        ):
            pass

    # 验证 stop_sequences 被正确传递
    call_kwargs = mock_beta_messages.stream.call_args[1]
    assert "stop_sequences" in call_kwargs
    assert call_kwargs["stop_sequences"] == stop_tokens
