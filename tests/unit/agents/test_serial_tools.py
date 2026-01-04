"""测试串行工具调用功能

验证 ResponseHandler 能正确处理多个串行的工具调用。

与并行执行的区别：
- 并行：所有工具同时执行，然后一次性收集结果
- 串行：工具按顺序执行，一个完成后才执行下一个
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import ToolUseBlock

from mind.agents.response import ResponseHandler


async def _async_iter(events):
    """将列表转换为 async iterator"""
    for event in events:
        yield event


@pytest.mark.asyncio
async def test_serial_tool_calls_execution():
    """测试多个工具调用能够串行执行

    Given: API 返回两个 search_web 工具调用
    When: 处理这些工具调用（串行模式）
    Then: 应该串行执行两个搜索，按顺序完成
    """
    # Arrange - 创建 mock client
    mock_client = MagicMock()
    mock_client.stream = lambda *args, **kwargs: _async_iter(events)

    # 模拟流式响应：两个并行的 search_web 工具调用
    tool_use_1 = ToolUseBlock(
        type="tool_use",
        id="toolu_01",
        name="search_web",
        input={"query": "量子计算"},
    )
    tool_use_2 = ToolUseBlock(
        type="tool_use",
        id="toolu_02",
        name="search_web",
        input={"query": "AI 进展"},
    )

    # 创建模拟事件流
    events = [
        MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_delta",
            delta=MagicMock(type="text_delta", text="让我搜索一下..."),
        ),
        MagicMock(type="content_block_stop", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_1,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_1),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_2,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_2),
        MagicMock(type="message_stop", stop_reason="tool_use"),
    ]

    # 创建 ResponseHandler
    handler = ResponseHandler(
        client=mock_client,
        search_history=None,
        search_config=None,
        name="TestAgent",
        documents=None,
    )

    # Mock 搜索执行 - 记录调用顺序和时间
    execution_order = []
    execution_times = []

    async def mock_execute(tool_call, messages, system, interrupt):
        query = tool_call["input"]["query"]
        execution_order.append(query)
        execution_times.append(asyncio.get_event_loop().time())
        # 模拟搜索耗时
        await asyncio.sleep(0.1)
        return f"搜索结果: {query}"

    async def mock_continue(messages, system, interrupt):
        return "基于搜索结果的响应"

    with (
        patch.object(handler, "_execute_tool_search", side_effect=mock_execute),
        patch.object(handler, "_continue_response", side_effect=mock_continue),
    ):
        # Act - 执行响应
        messages = []
        interrupt = asyncio.Event()
        await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证串行执行
    assert len(execution_order) == 2, "应该执行两个工具调用"
    assert "量子计算" in execution_order
    assert "AI 进展" in execution_order

    # 验证是串行执行：两个工具的执行时间差应该 > 0.1秒
    # 第一个工具完成后，第二个才开始
    time_diff = abs(execution_times[1] - execution_times[0])
    assert time_diff >= 0.1, f"工具应该串行执行，但时间差为 {time_diff:.3f}秒，疑似并行"


@pytest.mark.asyncio
async def test_serial_tool_calls_preserve_order():
    """测试串行执行时工具调用顺序被保留

    Given: 多个工具调用
    When: 串行执行这些工具
    Then: 结果应该按调用顺序添加到消息
    """
    # Arrange
    mock_client = MagicMock()

    tool_use_1 = ToolUseBlock(
        type="tool_use",
        id="toolu_01",
        name="search_web",
        input={"query": "first_query"},
    )
    tool_use_2 = ToolUseBlock(
        type="tool_use",
        id="toolu_02",
        name="search_web",
        input={"query": "second_query"},
    )
    tool_use_3 = ToolUseBlock(
        type="tool_use",
        id="toolu_03",
        name="search_web",
        input={"query": "third_query"},
    )

    events = [
        MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_delta",
            delta=MagicMock(type="text_delta", text="搜索中..."),
        ),
        MagicMock(type="content_block_stop", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_1,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_1),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_2,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_2),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_3,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_3),
        MagicMock(type="message_stop", stop_reason="tool_use"),
    ]

    mock_client.stream = lambda *args, **kwargs: _async_iter(events)

    handler = ResponseHandler(
        client=mock_client,
        search_history=MagicMock(),
        search_config=MagicMock(),
        name="TestAgent",
        documents=None,
    )

    # Mock 搜索执行
    execution_order = []

    async def mock_execute(tool_call, messages, system, interrupt):
        query = tool_call["input"]["query"]
        execution_order.append(query)
        return f"结果: {query}"

    async def mock_continue(messages, system, interrupt):
        return "完成"

    with (
        patch.object(handler, "_execute_tool_search", side_effect=mock_execute),
        patch.object(handler, "_continue_response", side_effect=mock_continue),
    ):
        messages = []
        interrupt = asyncio.Event()
        await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证执行顺序
    assert execution_order == ["first_query", "second_query", "third_query"]


@pytest.mark.asyncio
async def test_serial_tool_single_result_per_message():
    """测试串行执行时工具结果格式正确

    Given: 执行了多个工具调用（串行）
    When: 将结果添加到消息历史
    Then: 应该在一个 user 消息中包含多个 tool_result
        （格式与并行版本保持一致）
    """
    # Arrange
    mock_client = MagicMock()

    tool_use_1 = ToolUseBlock(
        type="tool_use",
        id="toolu_01",
        name="search_web",
        input={"query": "query1"},
    )
    tool_use_2 = ToolUseBlock(
        type="tool_use",
        id="toolu_02",
        name="search_web",
        input={"query": "query2"},
    )

    events = [
        MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_delta",
            delta=MagicMock(type="text_delta", text="搜索中..."),
        ),
        MagicMock(type="content_block_stop", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_1,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_1),
        MagicMock(
            type="content_block_start",
            content_block=tool_use_2,
        ),
        MagicMock(type="content_block_stop", content_block=tool_use_2),
        MagicMock(type="message_stop", stop_reason="tool_use"),
    ]

    mock_client.stream = lambda *args, **kwargs: _async_iter(events)

    handler = ResponseHandler(
        client=mock_client,
        search_history=MagicMock(),
        search_config=MagicMock(),
        name="TestAgent",
        documents=None,
    )

    async def mock_continue(messages, system, interrupt):
        return "基于搜索结果的响应"

    async def mock_search(tool_call, messages, system, interrupt):
        return f"搜索结果: {tool_call['input']['query']}"

    with (
        patch.object(handler, "_continue_response", side_effect=mock_continue),
        patch.object(handler, "_execute_tool_search", side_effect=mock_search),
    ):
        messages = []
        interrupt = asyncio.Event()
        await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证消息格式与并行版本一致
    assert len(messages) >= 2

    # 查找 assistant 消息（包含 tool_use）
    assistant_msg = None
    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_use":
                        assistant_msg = msg
                        break
            break

    # 查找 user 消息（包含 tool_result）
    user_msg = None
    for msg in messages:
        if msg.get("role") == "user":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "tool_result":
                        user_msg = msg
                        break
            break

    # 验证格式正确
    assert assistant_msg is not None, "应该有包含 tool_use 的 assistant 消息"
    assert user_msg is not None, "应该有包含 tool_result 的 user 消息"
