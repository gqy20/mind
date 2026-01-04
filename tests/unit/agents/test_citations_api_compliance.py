"""测试 Citations API 实现符合官方规范

验证项目对 Anthropic Citations API 的实现是否符合官方规范。
参考：https://platform.claude.com/docs/en/api/messages
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_citations_delta_event_has_single_citation():
    """验证 citations_delta 事件包含单个 citation 对象（官方规范）

    Given: 模拟一个 citations_delta 事件
    When: 处理该事件
    Then: 应该使用 event.delta.citation（单数）而不是 citations（复数）

    官方规范：
    CitationsDelta = {
        "type": "citations_delta",
        "citation": CitationCharLocation | CitationContentBlockLocation | ...
    }
    """
    from mind.agents.client import AnthropicClient

    # 创建 mock 客户端
    mock_client = AnthropicClient(model="claude-sonnet-4-5-20250929")

    # 模拟 citations_delta 事件（使用官方规范格式）
    mock_event = MagicMock()
    mock_event.type = "content_block_delta"
    mock_event.delta.type = "citations_delta"
    mock_event.delta.citation = MagicMock(  # 注意：citation 是单数
        type="char_location",
        cited_text="测试引用文本",
        document_title="测试文档",
        document_index=0,
        start_char_index=10,
        end_char_index=20,
    )

    # 模拟流式响应
    async def mock_stream(*args, **kwargs):
        yield mock_event
        # 生成一个结束事件
        stop_event = MagicMock()
        stop_event.type = "content_block_stop"
        stop_event.content_block = MagicMock(type="text")
        yield stop_event

    with patch.object(mock_client.client.beta.messages, "stream") as mock_stream_method:
        mock_stream_method.return_value.__aenter__.return_value = mock_stream

        # 执行并验证
        citations_buffer = []
        async for event in mock_client.stream(
            messages=[{"role": "user", "content": "test"}],
            system="test",
        ):
            if event.type == "content_block_delta":
                if event.delta.type == "citations_delta":
                    # 官方规范：使用 event.delta.citation（单数）
                    assert hasattr(event.delta, "citation"), (
                        "citations_delta 事件应包含 citation（单数）字段"
                    )
                    citation = event.delta.citation
                    citations_buffer.append(
                        {
                            "type": getattr(citation, "type", "unknown"),
                            "document_title": getattr(
                                citation, "document_title", "未知来源"
                            ),
                            "cited_text": getattr(citation, "cited_text", ""),
                            "document_index": getattr(citation, "document_index", 0),
                        }
                    )

        # 验证捕获的引用数据
        assert len(citations_buffer) == 1
        assert citations_buffer[0]["document_title"] == "测试文档"
        assert citations_buffer[0]["cited_text"] == "测试引用文本"
        assert citations_buffer[0]["document_index"] == 0


@pytest.mark.asyncio
async def test_response_handler_captures_document_index():
    """验证 ResponseHandler 捕获 document_index 字段

    Given: citations_delta 事件包含 document_index
    When: ResponseHandler 处理事件
    Then: document_index 应该被正确捕获
    """
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    mock_client = AnthropicClient(model="claude-sonnet-4-5-20250929")
    handler = ResponseHandler(mock_client)

    # 模拟 citations_delta 事件（包含 document_index）
    mock_event = MagicMock()
    mock_event.type = "content_block_delta"
    mock_event.delta.type = "citations_delta"
    mock_event.delta.citation = MagicMock(
        type="content_block_location",
        cited_text="引用内容",
        document_title="文档A",
        document_index=2,  # 重要的：document_index
        start_block_index=0,
        end_block_index=1,
    )

    # 处理事件
    response_text = ""
    citations_buffer = []
    response_text, _, new_citations = handler._handle_content_block_delta(
        mock_event, response_text, False
    )
    citations_buffer.extend(new_citations)

    # 验证：应该包含 document_index
    assert len(citations_buffer) == 1
    assert citations_buffer[0]["document_index"] == 2, (
        "ResponseHandler 应该捕获 document_index 字段"
    )


@pytest.mark.asyncio
async def test_citations_include_all_required_fields():
    """验证捕获的引用包含所有必需字段

    Given: 一个完整的 citations_delta 事件
    When: 处理该事件
    Then: 所有必需字段（type, document_title, cited_text, document_index）都被捕获
    """
    from mind.agents.client import AnthropicClient
    from mind.agents.response import ResponseHandler

    mock_client = AnthropicClient(model="claude-sonnet-4-5-20250929")
    handler = ResponseHandler(mock_client)

    # 模拟完整的 citations_delta 事件
    mock_event = MagicMock()
    mock_event.type = "content_block_delta"
    mock_event.delta.type = "citations_delta"
    mock_event.delta.citation = MagicMock(
        type="search_result_location",
        cited_text="搜索结果引用",
        document_title="搜索: Python教程",
        document_index=1,
        start_block_index=0,
        end_block_index=2,
        search_result_index=0,
        source="google",
    )

    response_text = ""
    _, _, citations = handler._handle_content_block_delta(
        mock_event, response_text, False
    )

    # 验证所有必需字段
    assert len(citations) == 1
    citation = citations[0]

    # 必需字段检查
    assert "type" in citation
    assert "document_title" in citation
    assert "cited_text" in citation
    assert "document_index" in citation

    # 值检查
    assert citation["type"] == "search_result_location"
    assert citation["document_title"] == "搜索: Python教程"
    assert citation["cited_text"] == "搜索结果引用"
    assert citation["document_index"] == 1


def test_current_implementation_issues():
    """通过代码检查验证当前实现的问题

    这个测试不需要运行，用于记录当前实现与规范的差异。
    """
    import inspect

    from mind.agents.response import ResponseHandler

    source = inspect.getsource(ResponseHandler._handle_content_block_delta)

    # 问题 1：当前使用 citations（复数），应该使用 citation（单数）
    assert "event.delta.citations" in source, (
        "❌ 当前实现使用 event.delta.citations（复数）"
        "\n✅ 官方规范要求 event.delta.citation（单数）"
    )

    # 问题 2：缺少 document_index 字段
    assert "document_index" not in source, (
        "❌ 当前实现缺少 document_index 字段\n✅ 官方规范要求包含 document_index"
    )


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
