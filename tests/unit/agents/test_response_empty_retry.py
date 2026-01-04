"""测试空响应重试机制

当 AI 在继续生成时只调用工具而不输出内容，系统应自动重试一次，
并在重试时禁止工具调用，强制 AI 输出内容。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_continue_response_empty_response_triggers_retry():
    """测试继续生成时空响应触发重试机制"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # 第一次调用：AI 只返回工具调用，没有文本内容
    first_call_events = []
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.delta = MagicMock()
    tool_event.delta.type = "tool_use"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_0123"
    tool_event.content_block.input = {"query": "test"}
    first_call_events.append(tool_event)

    async def first_call_iter():
        for event in first_call_events:
            yield event

    first_stream = MagicMock()
    first_stream.__aenter__ = AsyncMock(return_value=first_call_iter())
    first_stream.__aexit__ = AsyncMock(return_value=None)

    # 第二次调用（重试）：AI 输出文本内容
    second_call_events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "根据搜索结果，答案是..."
    second_call_events.append(text_event)

    async def second_call_iter():
        for event in second_call_events:
            yield event

    second_stream = MagicMock()
    second_stream.__aenter__ = AsyncMock(return_value=second_call_iter())
    second_stream.__aexit__ = AsyncMock(return_value=None)

    # 设置 mock_anthropic 返回不同的流
    mock_anthropic = MagicMock()
    stream_call_count = [0]

    def get_stream(*args, **kwargs):
        stream_call_count[0] += 1
        if stream_call_count[0] == 1:
            return first_stream
        else:
            return second_stream

    mock_anthropic.messages.stream = MagicMock(side_effect=get_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        # 调用 _continue_response
        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：应该调用了两次 API（第一次工具，第二次重试）
    assert mock_anthropic.messages.stream.call_count == 2
    # 验证：返回重试后的文本内容
    assert "答案是" in result


@pytest.mark.asyncio
async def test_continue_response_with_text_no_retry():
    """测试继续生成时有文本内容不触发重试"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # AI 在工具调用前已经输出了文本
    events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "让我搜索一下..."
    events.append(text_event)

    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.delta = MagicMock()
    tool_event.delta.type = "tool_use"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_0123"
    tool_event.content_block.input = {"query": "test"}
    events.append(tool_event)

    async def mock_iter():
        for event in events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    mock_anthropic.messages.stream = MagicMock(return_value=mock_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：只调用一次 API（没有重试）
    assert mock_anthropic.messages.stream.call_count == 1
    # 验证：返回已生成的文本
    assert "让我搜索一下" in result


@pytest.mark.asyncio
async def test_continue_response_retry_without_tools():
    """测试重试时不传入 tools 参数"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # 第一次调用：只有工具
    first_call_events = []
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.delta = MagicMock()
    tool_event.delta.type = "tool_use"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_0123"
    tool_event.content_block.input = {"query": "test"}
    first_call_events.append(tool_event)

    async def first_call_iter():
        for event in first_call_events:
            yield event

    first_stream = MagicMock()
    first_stream.__aenter__ = AsyncMock(return_value=first_call_iter())
    first_stream.__aexit__ = AsyncMock(return_value=None)

    # 第二次调用：输出文本
    second_call_events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "这是重试后的回答"
    second_call_events.append(text_event)

    async def second_call_iter():
        for event in second_call_events:
            yield event

    second_stream = MagicMock()
    second_stream.__aenter__ = AsyncMock(return_value=second_call_iter())
    second_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    call_count = [0]
    call_kwargs_list = []

    def get_stream(*args, **kwargs):
        call_count[0] += 1
        call_kwargs_list.append(kwargs)
        if call_count[0] == 1:
            return first_stream
        else:
            return second_stream

    mock_anthropic.messages.stream = MagicMock(side_effect=get_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：第一次调用有 tools 参数
    first_call_kwargs = call_kwargs_list[0]
    assert "tools" in first_call_kwargs
    assert first_call_kwargs["tools"] is not None

    # 验证：第二次调用（重试）没有 tools 参数
    second_call_kwargs = call_kwargs_list[1]
    assert "tools" not in second_call_kwargs or second_call_kwargs.get("tools") is None


@pytest.mark.asyncio
async def test_continue_response_max_one_retry():
    """测试最多重试一次，避免无限循环"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # 所有调用都只返回工具，没有文本
    events = []
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.delta = MagicMock()
    tool_event.delta.type = "tool_use"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_0123"
    tool_event.content_block.input = {"query": "test"}
    events.append(tool_event)

    async def mock_iter():
        for event in events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    mock_anthropic.messages.stream = MagicMock(return_value=mock_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：最多调用 2 次（初始 + 1 次重试）
    assert mock_anthropic.messages.stream.call_count <= 2
    # 验证：返回空字符串
    assert result == ""


@pytest.mark.asyncio
async def test_continue_response_retry_enhanced_system_prompt():
    """测试重试时增强系统提示词"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # 第一次调用：只有工具
    first_call_events = []
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.delta = MagicMock()
    tool_event.delta.type = "tool_use"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_0123"
    tool_event.content_block.input = {"query": "test"}
    first_call_events.append(tool_event)

    async def first_call_iter():
        for event in first_call_events:
            yield event

    first_stream = MagicMock()
    first_stream.__aenter__ = AsyncMock(return_value=first_call_iter())
    first_stream.__aexit__ = AsyncMock(return_value=None)

    # 第二次调用：输出文本
    second_call_events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "重试后的回答"
    second_call_events.append(text_event)

    async def second_call_iter():
        for event in second_call_events:
            yield event

    second_stream = MagicMock()
    second_stream.__aenter__ = AsyncMock(return_value=second_call_iter())
    second_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    call_count = [0]
    system_prompts = []

    def get_stream(*args, **kwargs):
        call_count[0] += 1
        system_prompts.append(kwargs.get("system", ""))
        if call_count[0] == 1:
            return first_stream
        else:
            return second_stream

    mock_anthropic.messages.stream = MagicMock(side_effect=get_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：第一次使用原始系统提示词
    original_system = system_prompts[0]
    assert original_system == "You are helpful"

    # 验证：第二次使用增强的系统提示词
    retry_system = system_prompts[1]
    assert "搜索已完成" in retry_system or "直接输出" in retry_system


@pytest.mark.asyncio
async def test_continue_response_no_tool_call_no_retry():
    """测试没有工具调用时不触发重试"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # AI 直接输出文本，没有工具调用
    events = []
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "这是回答"
    events.append(text_event)

    async def mock_iter():
        for event in events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    mock_anthropic.messages.stream = MagicMock(return_value=mock_stream)

    with patch.object(
        AnthropicClient,
        "__init__",
        lambda self, model, api_key=None, base_url=None: None,
    ):
        client = AnthropicClient(model="test-model", api_key="test-key")
        client.model = "test-model"
        client.client = mock_anthropic

        handler = ResponseHandler(client)

        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=asyncio.Event(),
        )

    # 验证：只调用一次
    assert mock_anthropic.messages.stream.call_count == 1
    # 验证：返回文本内容
    assert result == "这是回答"
