"""测试 ResponseHandler 正确传递 system 参数

验证在工具调用后继续生成响应时，system 参数被正确传递。
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import ToolUseBlock


async def _async_iter(events):
    """将列表转换为 async iterator"""
    for event in events:
        yield event


@pytest.mark.asyncio
async def test_respond_passes_system_to_continue():
    """测试 respond 方法在工具调用后正确传递 system 参数给 _continue_response

    Given: respond 方法使用 system 参数调用
    When: 检测到工具调用并执行
    Then: _continue_response 应该收到原始的 system 参数
    """
    # Arrange
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.model = "test-model"

    # 记录 _continue_response 的调用
    continue_calls = []

    async def mock_continue(self, messages, system, interrupt):
        continue_calls.append(system)
        return "继续响应"

    tool_use_1 = ToolUseBlock(
        type="tool_use",
        id="toolu_01",
        name="search_web",
        input={"query": "test"},
    )

    events = [
        MagicMock(type="content_block_start", content_block=tool_use_1),
        MagicMock(type="content_block_stop", content_block=tool_use_1),
        MagicMock(type="message_stop", stop_reason="tool_use"),
    ]

    mock_client.stream = lambda *args, **kwargs: _async_iter(events)

    handler = ResponseHandler(client=mock_client)

    system_prompt = "You are a helpful assistant"

    # Mock 搜索工具（需要支持新的签名）
    async def mock_search(tool_call, messages, system, interrupt):
        return "搜索结果"

    with patch.object(ResponseHandler, "_continue_response", mock_continue):
        with patch.object(handler, "_execute_tool_search", side_effect=mock_search):
            messages = []
            interrupt = asyncio.Event()
            await handler.respond(messages, system_prompt, interrupt)

    # Assert - 验证修复后 _continue_response 收到正确的 system 参数
    assert len(continue_calls) >= 1
    assert continue_calls[0] == system_prompt, (
        f"_continue_response 应该收到原始 system '{system_prompt}'，"
        f"但得到 '{continue_calls[0]}'"
    )


def test_execute_tools_serial_passes_system():
    """测试 _execute_tools_serial 正确传递 system 参数

    通过代码检查验证修复后的正确行为。
    """
    import inspect

    from mind.agents.response import ResponseHandler

    # 获取源码
    source = inspect.getsource(ResponseHandler._execute_tools_serial)

    # 验证代码中正确传递 system 参数
    assert "_continue_response(messages, system, interrupt)" in source, (
        "_execute_tools_serial 应该传递 system 参数给 _continue_response"
    )


def test_execute_tool_search_passes_system():
    """测试 _execute_tool_search 正确传递 system 参数

    通过代码检查验证修复后的正确行为。
    """
    import inspect

    from mind.agents.response import ResponseHandler

    # 获取源码
    source = inspect.getsource(ResponseHandler._execute_tool_search)

    # 验证代码中正确传递 system 参数（应该有两处）
    assert "_continue_response(messages, system, interrupt)" in source, (
        "修复后 _execute_tool_search 应该传递 system 参数给 _continue_response"
    )
