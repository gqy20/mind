"""测试重试时机优化

确保重试只在响应完全结束后触发，避免双重输出问题。
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_retry_only_after_stream_ends():
    """测试重试只在流式响应完全结束后触发

    Given: AI 在 _continue_response 中只返回工具调用，没有文本
    When: 流式响应循环结束后
    Then: 才触发重试机制
    And: 不会在流式过程中过早触发
    """
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # Mock 事件流：只有工具调用，没有文本
    events = []

    # 工具调用事件
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_123"
    tool_event.content_block.input = {"query": "test"}
    events.append(tool_event)

    # 没有文本事件，所以 response_text 保持为空

    async def mock_stream(**kwargs):
        for event in events:
            yield event

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = mock_stream
    mock_client.model = "test-model"

    # Mock _retry_without_tools 来检测是否被调用
    retry_called = False

    async def mock_retry(self, messages, system, interrupt):
        nonlocal retry_called
        retry_called = True
        return "重试后的内容"

    # 创建不会被中断的 interrupt
    interrupt = MagicMock()
    interrupt.is_set.return_value = False

    with patch.object(ResponseHandler, "_retry_without_tools", mock_retry):
        handler = ResponseHandler(mock_client)
        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=interrupt,
        )

    # 验证：因为只有工具调用没有文本，应该触发重试
    assert retry_called, "应该触发重试机制"
    assert result == "重试后的内容"


@pytest.mark.asyncio
async def test_no_retry_when_stream_has_text():
    """测试当流式响应有文本时不触发重试

    Given: AI 在 _continue_response 中返回工具调用 + 文本
    When: 流式响应循环结束
    Then: 不触发重试机制
    """
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # Mock 事件流：工具调用 + 文本
    events = []

    # 工具调用事件
    tool_event = MagicMock()
    tool_event.type = "content_block_stop"
    tool_event.content_block = MagicMock()
    tool_event.content_block.type = "tool_use"
    tool_event.content_block.name = "search_web"
    tool_event.content_block.id = "toolu_123"
    tool_event.content_block.input = {"query": "test"}
    events.append(tool_event)

    # 文本事件
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "这是搜索后的回答"
    events.append(text_event)

    async def mock_stream(**kwargs):
        for event in events:
            yield event

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = mock_stream
    mock_client.model = "test-model"

    # Mock _retry_without_tools 来检测是否被调用
    retry_called = False

    async def mock_retry(self, messages, system, interrupt):
        nonlocal retry_called
        retry_called = True
        return "不应该被调用"

    # 创建不会被中断的 interrupt
    interrupt = MagicMock()
    interrupt.is_set.return_value = False

    with patch.object(ResponseHandler, "_retry_without_tools", mock_retry):
        handler = ResponseHandler(mock_client)
        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=interrupt,
        )

    # 验证：因为有文本，不应该触发重试
    assert not retry_called, "不应该触发重试机制"
    assert result == "这是搜索后的回答"


@pytest.mark.asyncio
async def test_retry_after_stream_complete_no_early_trigger():
    """测试重试不会在流式过程中过早触发

    Given: AI 先返回工具调用，然后可能会返回文本
    When: 工具调用事件处理完后，但流式循环还未结束
    Then: 不立即触发重试，而是等待流式循环结束
    """
    # 使用异步队列模拟真实的流式时序
    import asyncio

    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    async def mock_stream(**kwargs):
        # 先发送工具调用事件
        tool_event = MagicMock()
        tool_event.type = "content_block_stop"
        tool_event.content_block = MagicMock()
        tool_event.content_block.type = "tool_use"
        tool_event.content_block.name = "search_web"
        tool_event.content_block.id = "toolu_123"
        tool_event.content_block.input = {"query": "test"}
        yield tool_event

        # 模拟延迟（模拟 AI 思考时间）
        await asyncio.sleep(0.01)

        # 再发送文本事件
        text_event = MagicMock()
        text_event.type = "content_block_delta"
        text_event.delta.type = "text_delta"
        text_event.delta.text = "延迟的回答"
        yield text_event

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = mock_stream
    mock_client.model = "test-model"

    # Mock _retry_without_tools 来检测是否被调用
    retry_called = False

    async def mock_retry(self, messages, system, interrupt):
        nonlocal retry_called
        retry_called = True
        return "不应该被调用"

    # 创建不会被中断的 interrupt
    interrupt = MagicMock()
    interrupt.is_set.return_value = False

    with patch.object(ResponseHandler, "_retry_without_tools", mock_retry):
        handler = ResponseHandler(mock_client)
        result = await handler._continue_response(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=interrupt,
        )

    # 验证：虽然有延迟，但最终有文本，不应该触发重试
    assert not retry_called, "不应该触发重试机制（流式循环结束后有文本）"
    assert result == "延迟的回答"


@pytest.mark.asyncio
async def test_stream_loop_naturally_ending_marks_completion():
    """测试流式循环自然结束标志着响应完成

    Given: AI 的流式响应
    When: async for 循环自然退出（没有更多事件）
    Then: 认为响应已完成，可以检查是否需要重试
    """
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    async def mock_stream(**kwargs):
        # 立即结束，不产生任何事件
        return
        yield  # 使其成为生成器函数

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = mock_stream
    mock_client.model = "test-model"

    # 创建不会被中断的 interrupt
    interrupt = MagicMock()
    interrupt.is_set.return_value = False

    handler = ResponseHandler(mock_client)
    result = await handler._continue_response(
        messages=[{"role": "user", "content": "test"}],
        system="You are helpful",
        interrupt=interrupt,
    )

    # 验证：空流应该返回空字符串
    assert result == ""
