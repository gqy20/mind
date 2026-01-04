"""测试 Citations API 需要使用 beta API

这个测试验证 Citations API 只能通过 client.beta.messages 访问
"""

import pytest


@pytest.mark.asyncio
async def test_beta_api_has_citations_support():
    """验证 beta API 支持 Citations 功能"""
    from anthropic import AsyncAnthropic

    # 创建客户端
    client = AsyncAnthropic(api_key="test-key")

    # 验证 beta 属性存在
    assert hasattr(client, "beta"), "AsyncAnthropic 应该有 beta 属性"
    assert hasattr(client.beta, "messages"), "beta 应该有 messages 属性"

    # 验证 beta.messages 有 stream 方法
    assert hasattr(client.beta.messages, "stream"), "beta.messages 应该有 stream 方法"


def test_sdk_has_beta_citations_types():
    """验证 SDK 包含 Citations 相关的 Beta 类型"""
    from anthropic.types.beta import BetaCitationsDelta

    # 验证 BetaCitationsDelta 类型存在
    assert BetaCitationsDelta is not None

    # 验证类型结构
    delta = BetaCitationsDelta(
        type="citations_delta",
        citation={
            "type": "char_location",
            "cited_text": "测试文本",
            "document_index": 0,
            "document_title": "测试文档",
            "start_char_index": 0,
            "end_char_index": 10,
        },
    )

    assert delta.type == "citations_delta"
    assert delta.citation.cited_text == "测试文本"


def test_sdk_has_beta_citations_event_types():
    """验证 SDK 包含 Citations 事件类型"""
    # 导入所有需要的类型
    from anthropic.types.beta import (
        BetaCitationContentBlockLocation,
        BetaCitationsDelta,
    )

    # 创建一个内容块位置引用
    content_block_citation = BetaCitationContentBlockLocation(
        type="content_block_location",
        cited_text="测试引用内容",
        document_index=0,
        document_title="测试文档",
        start_block_index=0,
        end_block_index=1,
    )

    assert content_block_citation.type == "content_block_location"
    assert content_block_citation.cited_text == "测试引用内容"

    # 创建一个 citations_delta 事件
    delta = BetaCitationsDelta(
        type="citations_delta",
        citation=content_block_citation,
    )

    assert delta.type == "citations_delta"
    assert delta.citation == content_block_citation
