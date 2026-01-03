"""测试工具消息构建方法的提取

测试从 _execute_tool_search() 中提取的重复消息构建逻辑。
"""

from unittest.mock import MagicMock

import pytest

from mind.agents.client import AnthropicClient
from mind.agents.response import ResponseHandler


@pytest.mark.asyncio
async def test_append_tool_messages_basic():
    """测试添加工具调用和结果消息

    Given: 工具调用信息、查询和结果文本
    When: 调用 _append_tool_messages
    Then: 正确添加两条消息到消息列表
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    tool_call = {
        "id": "tool-123",
        "name": "search_web",
        "input": {"query": "test query"},
    }

    messages = []
    query = "test query"
    result_text = "找到 3 条结果"

    handler._append_tool_messages(messages, tool_call, query, result_text)

    # 验证添加了两条消息
    assert len(messages) == 2

    # 验证第一条消息（tool_use）
    assert messages[0]["role"] == "assistant"
    assert messages[0]["content"][0]["type"] == "tool_use"
    assert messages[0]["content"][0]["id"] == "tool-123"
    assert messages[0]["content"][0]["name"] == "search_web"
    assert messages[0]["content"][0]["input"]["query"] == "test query"

    # 验证第二条消息（tool_result）
    assert messages[1]["role"] == "user"
    assert messages[1]["content"][0]["type"] == "tool_result"
    assert messages[1]["content"][0]["tool_use_id"] == "tool-123"
    assert messages[1]["content"][0]["content"] == "找到 3 条结果"


@pytest.mark.asyncio
async def test_append_tool_messages_preserves_existing_messages():
    """测试保留消息列表中已有的消息

    Given: 已有消息的列表
    When: 调用 _append_tool_messages
    Then: 已有消息被保留，新消息追加到末尾
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    tool_call = {"id": "t1", "name": "search_web", "input": {"query": "q"}}
    messages = [{"role": "user", "content": "之前的消息"}]

    handler._append_tool_messages(messages, tool_call, "q", "结果")

    # 验证原有消息被保留
    assert len(messages) == 3
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "之前的消息"


@pytest.mark.asyncio
async def test_append_tool_messages_with_empty_result():
    """测试空结果文本的处理

    Given: 空字符串作为结果文本
    When: 调用 _append_tool_messages
    Then: 消息仍然被正确添加，content 为空字符串
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    tool_call = {"id": "t1", "name": "search_web", "input": {"query": "q"}}
    messages = []

    handler._append_tool_messages(messages, tool_call, "q", "")

    # 验证消息被添加
    assert len(messages) == 2
    assert messages[1]["content"][0]["content"] == ""


@pytest.mark.asyncio
async def test_append_tool_messages_with_special_characters():
    """测试包含特殊字符的查询和结果

    Given: 查询和结果包含特殊字符
    When: 调用 _append_tool_messages
    Then: 特殊字符被正确保留
    """
    mock_client = MagicMock(spec=AnthropicClient)
    handler = ResponseHandler(client=mock_client)

    tool_call = {
        "id": "t1",
        "name": "search_web",
        "input": {"query": "查询: 测试 & <script>"},
    }
    messages = []

    handler._append_tool_messages(
        messages, tool_call, "查询: 测试 & <script>", "结果: \"引用\" '单引号'"
    )

    # 验证特殊字符被保留
    assert messages[0]["content"][0]["input"]["query"] == "查询: 测试 & <script>"
    assert messages[1]["content"][0]["content"] == "结果: \"引用\" '单引号'"
