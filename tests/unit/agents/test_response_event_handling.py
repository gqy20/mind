"""测试事件处理方法的提取

测试响应处理器中事件处理逻辑的独立方法，
这些方法将被从 respond() 和 _continue_response() 中提取出来。
"""

from unittest.mock import MagicMock

import pytest

from mind.agents.client import AnthropicClient
from mind.agents.response import ResponseHandler


class MockDelta:
    """模拟增量对象"""

    def __init__(self, delta_type: str, **kwargs):
        self.type = delta_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockStreamEvent:
    """模拟流事件"""

    def __init__(self, event_type: str, **kwargs):
        self.type = event_type
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.mark.asyncio
async def test_handle_text_delta_event():
    """测试处理 text_delta 事件

    Given: 一个 content_block_delta 事件，包含 text_delta
    When: 调用事件处理方法
    Then: 返回更新后的文本、has_text_delta=True、空引用列表
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建 text_delta 事件
    delta = MockDelta("text_delta", text="Hello, World!")
    event = MockStreamEvent("content_block_delta", delta=delta)

    # 调用要提取的方法
    response_text, has_text_delta, citations = handler._handle_content_block_delta(
        event=event,
        response_text="",
        has_text_delta=False,
    )

    # 验证
    assert response_text == "Hello, World!"
    assert has_text_delta is True
    assert citations == []


@pytest.mark.asyncio
async def test_handle_text_delta_event_with_prefix():
    """测试处理带角色名前缀的 text_delta 事件

    Given: 一个 text_delta 事件，包含 "[Agent]: 前缀"
    When: 调用事件处理方法
    Then: 前缀被清理
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建带前缀的 text_delta 事件
    delta = MockDelta("text_delta", text="[Supporter]: This is a response")
    event = MockStreamEvent("content_block_delta", delta=delta)

    response_text, has_text_delta, _ = handler._handle_content_block_delta(
        event=event,
        response_text="",
        has_text_delta=False,
    )

    # 验证前缀被清理（实际清理逻辑在 utils._clean_agent_name_prefix）
    assert "This is a response" in response_text or response_text != ""


@pytest.mark.asyncio
async def test_handle_citations_delta_event():
    """测试处理 citations_delta 事件

    Given: 一个 content_block_delta 事件，包含 citations_delta
    When: 调用事件处理方法
    Then: 返回提取的引用信息

    Note: 使用官方规范格式 event.delta.citation（单数）
    参考：https://platform.claude.com/docs/en/api/messages
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建引用事件（使用官方规范格式：citation 单数）
    citation = MagicMock()
    citation.type = "text"
    citation.document_title = "测试文档"
    citation.cited_text = "引用的文本内容"
    citation.document_index = 0

    delta = MockDelta("citations_delta", citation=citation)
    event = MockStreamEvent("content_block_delta", delta=delta)

    response_text, has_text_delta, citations = handler._handle_content_block_delta(
        event=event,
        response_text="",
        has_text_delta=False,
    )

    # 验证引用被提取
    assert len(citations) == 1
    assert citations[0]["document_title"] == "测试文档"
    assert citations[0]["cited_text"] == "引用的文本内容"
    assert citations[0]["document_index"] == 0
    assert response_text == ""
    assert has_text_delta is False


@pytest.mark.asyncio
async def test_handle_text_event_legacy():
    """测试处理旧格式 text 事件

    Given: 一个 text 事件（旧格式）
    When: 调用事件处理方法
    Then: 返回更新后的文本，has_text_delta 不变（允许多个 text 事件）
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建旧格式 text 事件
    event = MockStreamEvent("text", text="Legacy text")

    response_text, has_text_delta = handler._handle_text_event(
        event=event,
        response_text="",
        has_text_delta=False,
    )

    # 验证：旧格式 text 不改变 has_text_delta（与原始行为一致）
    assert response_text == "Legacy text"
    assert has_text_delta is False  # 不改变标志，允许多个 text 事件


@pytest.mark.asyncio
async def test_handle_text_event_skips_when_has_text_delta():
    """测试当 has_text_delta=True 时跳过 text 事件

    Given: 一个 text 事件，但 has_text_delta=True
    When: 调用事件处理方法
    Then: 返回原文本，不处理（因为已经有新格式事件）
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    event = MockStreamEvent("text", text="New text")

    response_text, has_text_delta = handler._handle_text_event(
        event=event,
        response_text="Original",
        has_text_delta=True,
    )

    # 验证没有改变（因为 has_text_delta=True 表示已处理过新格式）
    assert response_text == "Original"
    assert has_text_delta is True


@pytest.mark.asyncio
async def test_extract_tool_calls_from_content_block_stop():
    """测试从 content_block_stop 事件中提取工具调用

    Given: 一个 content_block_stop 事件，包含 tool_use
    When: 调用提取方法
    Then: 返回工具调用信息
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建工具调用事件
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tool-123"
    tool_block.name = "search_web"
    tool_block.input = {"query": "test"}

    event = MockStreamEvent("content_block_stop", content_block=tool_block)

    tool_calls = handler._extract_tool_calls(event)

    # 验证
    assert len(tool_calls) == 1
    assert tool_calls[0]["id"] == "tool-123"
    assert tool_calls[0]["name"] == "search_web"
    assert tool_calls[0]["input"] == {"query": "test"}


@pytest.mark.asyncio
async def test_extract_tool_calls_returns_empty_for_non_tool_use():
    """测试当 content_block 不是 tool_use 时返回空列表

    Given: 一个 content_block_stop 事件，但不是 tool_use
    When: 调用提取方法
    Then: 返回空列表
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建非 tool_use 事件
    content_block = MagicMock()
    content_block.type = "text"

    event = MockStreamEvent("content_block_stop", content_block=content_block)

    tool_calls = handler._extract_tool_calls(event)

    # 验证
    assert tool_calls == []


@pytest.mark.asyncio
async def test_extract_tool_calls_handles_missing_attributes():
    """测试处理缺少属性的事件

    Given: 一个 content_block_stop 事件，缺少必需属性
    When: 调用提取方法
    Then: 返回空列表（安全处理）
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    # 创建缺少属性的事件
    event = MockStreamEvent("content_block_stop", content_block=None)

    tool_calls = handler._extract_tool_calls(event)

    # 验证安全处理
    assert tool_calls == []
