"""测试响应处理的增强功能"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from anthropic import APIStatusError

from mind.agents.client import AnthropicClient
from mind.agents.response import ResponseHandler


class MockStreamEvent:
    """模拟流事件"""

    def __init__(self, event_type: str, **kwargs):
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockDelta:
    """模拟增量"""

    def __init__(self, delta_type: str, **kwargs):
        self.type = delta_type
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_respond_handles_tool_use():
    """测试响应处理器处理工具调用"""
    # 创建 mock client
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.model = "test-model"

    # 模拟流事件：包含工具调用
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool-123"
    tool_block.name = "search_web"
    tool_block.input = {"query": "test query"}

    events = [
        MockStreamEvent("content_block_stop", content_block=tool_block),
    ]

    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    # mock _execute_tool_search 方法
    with patch.object(handler, "_execute_tool_search") as mock_search:
        mock_search.return_value = None  # 模拟返回 None（表示不需要继续）
        await handler.respond(messages, "system prompt", interrupt)

    # 验证搜索被调用
    assert mock_search.called


@pytest.mark.asyncio
async def test_respond_handles_citations_delta():
    """测试响应处理器处理引用增量"""
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.model = "test-model"

    # 模拟引用事件
    citation = MagicMock()
    citation.type = "text"
    citation.document_title = "测试文档"
    citation.cited_text = "引用的文本内容"

    delta = MockDelta("citations_delta", citations=[citation])

    events = [
        MockStreamEvent("content_block_delta", delta=delta),
    ]

    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    await handler.respond(messages, "system prompt", interrupt)

    # 引用应该被捕获（可能在内部缓存中）
    # 这个测试主要验证不会崩溃，具体行为在实现后确定


@pytest.mark.asyncio
async def test_respond_handles_api_status_error():
    """测试 API 状态错误处理"""
    mock_client = MagicMock(spec=AnthropicClient)

    # 模拟 APIStatusError
    async def mock_stream(*args, **kwargs):
        response = MagicMock()
        response.status_code = 429
        raise APIStatusError(
            message="Rate limit exceeded",
            response=response,
            body=None,
        )

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    # 应该返回 None（错误处理）
    result = await handler.respond(messages, "system prompt", interrupt)
    _ = result  # 验证已处理错误
    assert result is None


@pytest.mark.asyncio
async def test_respond_handles_timeout_error():
    """测试超时错误处理"""
    mock_client = MagicMock(spec=AnthropicClient)

    # 模拟 TimeoutError
    async def mock_stream(*args, **kwargs):
        raise TimeoutError("Request timeout")

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    # 应该返回 None（错误处理）
    result = await handler.respond(messages, "system prompt", interrupt)
    _ = result  # 验证已处理错误
    assert result is None


@pytest.mark.asyncio
async def test_respond_handles_os_error():
    """测试网络错误处理"""
    mock_client = MagicMock(spec=AnthropicClient)

    # 模拟 OSError
    async def mock_stream(*args, **kwargs):
        raise OSError("Network error")

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    # 应该返回 None（错误处理）
    result = await handler.respond(messages, "system prompt", interrupt)
    _ = result  # 验证已处理错误
    assert result is None


@pytest.mark.asyncio
async def test_continue_response_basic():
    """测试 _continue_response 基本功能"""
    mock_client = MagicMock(spec=AnthropicClient)

    # 模拟文本事件
    events = [
        MockStreamEvent("text", text="Hello "),
        MockStreamEvent("text", text="World"),
    ]

    async def mock_stream(*args, **kwargs):
        for event in events:
            yield event

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = asyncio.Event()

    result = await handler._continue_response(messages, "system prompt", interrupt)

    assert result == "Hello World"


@pytest.mark.asyncio
async def test_continue_response_with_interrupt():
    """测试 _continue_response 中断处理"""
    mock_client = MagicMock(spec=AnthropicClient)

    # 创建一个可以在生成器内部访问的 interrupt
    test_interrupt = asyncio.Event()

    async def mock_stream(*args, **kwargs):
        yield MockStreamEvent("text", text="Before")
        test_interrupt.set()
        yield MockStreamEvent("text", text="After")

    mock_client.stream = mock_stream

    handler = ResponseHandler(client=mock_client)
    messages = [{"role": "user", "content": "test"}]
    interrupt = test_interrupt  # 使用同一个 interrupt

    result = await handler._continue_response(messages, "system prompt", interrupt)

    # 应该返回部分文本（中断前）
    assert "Before" in result


@pytest.mark.asyncio
async def test_execute_tool_search():
    """测试搜索工具执行"""
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    tool_call = {
        "id": "tool-123",
        "name": "search_web",
        "input": {"query": "test query"},
    }

    # mock _search_sync（在方法内部导入）
    with (
        patch("mind.tools.search_tool._search_sync") as mock_search_sync,
        patch("mind.tools.search_tool.search_web") as mock_search_web,
    ):
        mock_search_sync.return_value = [{"title": "结果1"}]
        mock_search_web.return_value = "搜索结果"

        await handler._execute_tool_search(
            tool_call,
            messages=[],
            interrupt=asyncio.Event(),
        )

    # 应该调用了搜索
    assert mock_search_sync.called or mock_search_web.called
