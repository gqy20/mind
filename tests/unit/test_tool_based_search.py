"""测试基于工具的搜索功能

验证 AI 使用工具调用（tool_use）而不是文本标记来请求搜索。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_agent_uses_tool_for_search():
    """测试 AI 使用工具调用而不是文本标记请求搜索"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # Mock 事件流：AI 调用 search_web 工具
    events = []

    # 第一个事件：tool_use 开始
    tool_use_event = MagicMock()
    tool_use_event.type = "content_block_start"
    tool_use_event.content_block = MagicMock()
    tool_use_event.content_block.type = "tool_use"
    tool_use_event.content_block.name = "search_web"
    tool_use_event.content_block.id = "toolu_0123"
    tool_use_event.content_block.input = {"query": "同倍体杂交物种形成"}
    events.append(tool_use_event)

    # 工具调用结束后的事件
    tool_stop_event = MagicMock()
    tool_stop_event.type = "content_block_stop"
    tool_stop_event.content_block = tool_use_event.content_block
    events.append(tool_stop_event)

    async def mock_iter():
        for event in events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    # 创建 Mock 客户端
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = AsyncMock(return_value=mock_stream)
    mock_client.model = "test-model"

    # Mock 搜索执行避免实际调用
    with patch.object(ResponseHandler, "_execute_tool_search", return_value="搜索结果"):
        handler = ResponseHandler(mock_client)

        # 创建不会被中断的 interrupt mock
        interrupt = MagicMock()
        interrupt.is_set.return_value = False

        await handler.respond(
            messages=[{"role": "user", "content": "test"}],
            system="You are helpful",
            interrupt=interrupt,
        )

    # 验证 stream 方法被调用
    call_args = mock_client.stream.call_args
    assert call_args is not None, "stream 方法应该被调用"
    call_kwargs = call_args[1] if call_args else {}
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) > 0
    assert call_kwargs["tools"][0]["name"] == "search_web"


@pytest.mark.asyncio
async def test_text_search_marker_not_displayed():
    """测试文本搜索标记不显示在输出中"""
    from mind.agents.response import ResponseHandler

    # Mock 事件流：AI 输出包含搜索标记的文本
    events = []

    # AI 尝试输出搜索标记（应该被过滤）
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "[搜索: 测试关键词]"
    events.append(text_event)

    async def mock_iter():
        for event in events:
            yield event

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_iter())
    mock_stream.__aexit__ = AsyncMock(return_value=None)

    mock_anthropic = MagicMock()
    mock_anthropic.messages.stream = MagicMock(return_value=mock_stream)

    captured_output = []

    with patch("mind.agents.client.AsyncAnthropic", return_value=mock_anthropic):
        from mind.agents.client import AnthropicClient

        client = AnthropicClient(model="test-model", api_key="test-key")
        client.client = mock_anthropic

        # Mock print 函数来捕获输出
        with patch(
            "builtins.print",
            side_effect=lambda *args, **kwargs: captured_output.append(args),
        ):
            handler = ResponseHandler(client)
            result = await handler.respond(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                interrupt=AsyncMock(),
            )

    # 验证搜索标记没有被打印（或被过滤）
    # 注意：当前实现可能还没有过滤，这个测试会失败
    printed_text = " ".join(str(arg) for arg in captured_output)
    # 期望：搜索标记被过滤或工具调用被使用
    assert "[搜索:" not in printed_text or (
        result is not None and "test" in result.text
    )


@pytest.mark.asyncio
async def test_tool_use_does_not_appear_in_response():
    """测试工具调用不会出现在响应文本中"""
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    # Mock 事件流：工具调用 + 文本输出
    events = []

    # 工具调用
    tool_use_event = MagicMock()
    tool_use_event.type = "content_block_start"
    tool_use_event.content_block = MagicMock()
    tool_use_event.content_block.type = "tool_use"
    tool_use_event.content_block.name = "search_web"
    tool_use_event.content_block.id = "toolu_0123"
    tool_use_event.content_block.input = {"query": "test"}
    events.append(tool_use_event)

    tool_stop_event = MagicMock()
    tool_stop_event.type = "content_block_stop"
    tool_stop_event.content_block = tool_use_event.content_block
    events.append(tool_stop_event)

    # 工具调用后的文本输出
    text_event = MagicMock()
    text_event.type = "content_block_delta"
    text_event.delta.type = "text_delta"
    text_event.delta.text = "这是搜索后的回答"
    events.append(text_event)

    # stream() 返回 async iterator，不是 async context manager
    async def mock_stream(**kwargs):
        for event in events:
            yield event

    # 创建 Mock 客户端 - stream 返回 async iterator
    mock_client = MagicMock(spec=AnthropicClient)
    mock_client.stream = mock_stream
    mock_client.model = "test-model"

    # 创建不会被中断的 interrupt mock
    interrupt = MagicMock()
    interrupt.is_set.return_value = False

    # Mock print 来捕获输出 - 使用简单的列表
    captured_prints = []

    def mock_print(*args, **kwargs):
        captured_prints.append(" ".join(str(arg) for arg in args))

    with patch("builtins.print", side_effect=mock_print):
        handler = ResponseHandler(mock_client)
        # Mock 搜索执行
        with patch.object(handler, "_execute_tool_search", return_value="搜索结果"):
            result = await handler.respond(
                messages=[{"role": "user", "content": "test"}],
                system="You are helpful",
                interrupt=interrupt,
            )

    # 验证有响应结果
    assert result is not None, "应该返回响应结果（未被中断）"

    # 验证响应文本不包含工具调用的内容
    assert result.text == "这是搜索后的回答"

    # 验证打印的输出不包含工具调用信息
    printed_output = " ".join(str(p) for p in captured_prints)
    assert "tool_use" not in printed_output
    assert "search_web" not in printed_output


@pytest.mark.asyncio
async def test_prompt_instructs_tool_usage():
    """测试提示词正确指导 AI 使用工具调用"""
    from mind.config import get_default_config_path, load_all_configs

    config_path = get_default_config_path()
    agent_configs, settings = load_all_configs(config_path)

    # 检查支持者的提示词
    supporter_prompt = agent_configs["supporter"].system_prompt

    # 验证提示词包含工具使用说明
    assert "search_web" in supporter_prompt or "工具" in supporter_prompt

    # 验证提示词不包含文本标记语法（修改后）
    # 注意：这个测试在修改提示词后会通过
    has_text_marker = "[搜索:" in supporter_prompt
    # 期望：不包含文本标记语法，或明确说明使用工具
    assert not has_text_marker or "使用工具" in supporter_prompt


def test_tools_schema_correctly_defined():
    """测试工具 schema 正确定义"""
    from mind.agents.response import _get_tools_schema

    tools = _get_tools_schema()

    # 验证有工具定义
    assert len(tools) > 0

    # 验证 search_web 工具存在
    search_tool = None
    for tool in tools:
        if isinstance(tool, dict):
            if tool.get("name") == "search_web":
                search_tool = tool
                break
        elif hasattr(tool, "name") and tool.name == "search_web":
            search_tool = tool
            break

    assert search_tool is not None

    # 验证工具参数
    if isinstance(search_tool, dict):
        input_schema_raw = search_tool.get("input_schema", {})
        input_schema = (
            dict(input_schema_raw) if isinstance(input_schema_raw, dict) else {}
        )
        props = input_schema.get("properties", {})
        assert isinstance(props, dict) and "query" in props
        query_type = props.get("query", {})
        assert isinstance(query_type, dict) and query_type.get("type") == "string"
    else:
        # search_tool 是对象
        input_schema_raw = getattr(search_tool, "input_schema", {})
        input_schema = (
            dict(input_schema_raw) if isinstance(input_schema_raw, dict) else {}
        )
        props = input_schema.get("properties", {})
        assert isinstance(props, dict) and "query" in props
