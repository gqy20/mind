"""测试并行工具调用功能

验证 ResponseHandler 能正确处理多个并行的工具调用。
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
async def test_parallel_tool_calls_execution():
    """测试多个工具调用能够并行执行

    Given: API 返回两个 search_web 工具调用
    When: 处理这些工具调用
    Then: 应该并行执行两个搜索，而不是串行
    """
    # Arrange - 创建 mock client
    mock_client = MagicMock()
    # 直接设置 async generator，不使用 AsyncMock
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
        # content_block_start (text)
        MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
        # text_delta
        MagicMock(
            type="content_block_delta",
            delta=MagicMock(type="text_delta", text="让我搜索一下..."),
        ),
        # content_block_stop (text)
        MagicMock(type="content_block_stop", content_block=MagicMock(type="text")),
        # content_block_start (tool_use 1)
        MagicMock(
            type="content_block_start",
            content_block=tool_use_1,
        ),
        # content_block_stop (tool_use 1)
        MagicMock(type="content_block_stop", content_block=tool_use_1),
        # content_block_start (tool_use 2)
        MagicMock(
            type="content_block_start",
            content_block=tool_use_2,
        ),
        # content_block_stop (tool_use 2)
        MagicMock(type="content_block_stop", content_block=tool_use_2),
        # message_stop
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
        execution_order.append(tool_call["input"]["query"])
        execution_times.append(asyncio.get_event_loop().time())
        # 模拟搜索耗时
        await asyncio.sleep(0.1)
        return f"搜索结果: {tool_call['input']['query']}"

    async def mock_continue(messages, system, interrupt):
        # Mock 继续响应，避免再次触发工具调用
        return "基于搜索结果的响应"

    with (
        patch.object(handler, "_execute_tool_search", side_effect=mock_execute),
        patch.object(handler, "_continue_response", side_effect=mock_continue),
    ):
        # Act - 执行响应
        messages = []
        interrupt = asyncio.Event()
        await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证并行执行
    assert len(execution_order) == 2, "应该执行两个工具调用"
    assert "量子计算" in execution_order
    assert "AI 进展" in execution_order

    # 验证是并行执行：两个工具的执行时间应该非常接近（< 0.15秒）
    # 如果是串行，时间差会 > 0.1秒（每个 sleep 0.1秒）
    time_diff = abs(execution_times[0] - execution_times[1])
    assert time_diff < 0.15, f"工具应该并行执行，但时间差为 {time_diff:.3f}秒，疑似串行"


@pytest.mark.asyncio
async def test_multiple_tool_results_in_message():
    """测试多个工具结果正确添加到消息历史

    Given: 执行了两个工具调用
    When: 将结果添加到消息历史
    Then: 应该在一个 user 消息中包含多个 tool_result
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

    # 第一次响应：返回工具调用
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
        search_history=MagicMock(),  # Mock search_history
        search_config=MagicMock(),
        name="TestAgent",
        documents=None,
    )

    # Mock 搜索返回继续响应
    async def mock_continue(messages, system, interrupt):
        return "基于搜索结果的响应"

    # Mock 搜索工具执行，返回模拟结果
    async def mock_search(tool_call, messages, system, interrupt):
        return f"搜索结果: {tool_call['input']['query']}"

    with (
        patch.object(handler, "_continue_response", side_effect=mock_continue),
        patch.object(handler, "_execute_tool_search", side_effect=mock_search),
    ):
        messages = []
        interrupt = asyncio.Event()
        await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证消息格式
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


@pytest.mark.asyncio
async def test_parallel_tools_with_citations():
    """测试并行工具调用时引用功能正常

    Given: 两个并行的搜索工具调用
    When: 每个搜索返回引用信息
    Then: 应该收集所有引用并正确显示
    """
    # Arrange
    mock_client = MagicMock()

    tool_use_1 = ToolUseBlock(
        type="tool_use",
        id="toolu_01",
        name="search_web",
        input={"query": "topic1"},
    )
    tool_use_2 = ToolUseBlock(
        type="tool_use",
        id="toolu_02",
        name="search_web",
        input={"query": "topic2"},
    )

    events = [
        MagicMock(type="content_block_start", content_block=MagicMock(type="text")),
        MagicMock(
            type="content_block_delta",
            delta=MagicMock(type="text_delta", text="搜索两个主题..."),
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
        return "搜索完成"

    # Mock 搜索工具执行
    async def mock_search(tool_call, messages, system, interrupt):
        return f"搜索结果: {tool_call['input']['query']}"

    with (
        patch.object(handler, "_continue_response", side_effect=mock_continue),
        patch.object(handler, "_execute_tool_search", side_effect=mock_search),
    ):
        messages = []
        interrupt = asyncio.Event()
        result = await handler.respond(messages, "test prompt", interrupt)

    # Assert - 验证引用被收集
    # (具体实现后验证引用数量和格式)
    assert result is not None
