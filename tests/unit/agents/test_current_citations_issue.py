"""测试 AnthropicClient 当前实现不支持 Citations API

这个测试验证项目当前的 AnthropicClient 没有使用 beta API
"""


def test_beta_api_usage():
    """演示应该如何使用 beta API 来支持 Citations"""

    from anthropic import AsyncAnthropic

    # 创建客户端
    client = AsyncAnthropic(api_key="test-key")

    # 验证 beta API 存在
    assert hasattr(client, "beta"), "AsyncAnthropic 应该有 beta 属性"
    assert hasattr(client.beta, "messages"), "beta 应该有 messages 属性"
    assert hasattr(client.beta.messages, "stream"), "beta.messages 应该有 stream 方法"

    # 正确的使用方式应该是：
    # async with client.beta.messages.stream(...) as stream:
    #     async for event in stream:
    #         if event.type == "content_block_delta":
    #             if event.delta.type == "citations_delta":
    #                 # 处理引用
    #                 pass


def test_current_implementation_uses_beta_api():
    """验证当前实现正确使用 beta API"""

    # 读取源码查看当前实现
    import inspect

    from mind.agents.client import AnthropicClient

    source = inspect.getsource(AnthropicClient.stream)

    # 验证当前实现使用 self.client.beta.messages.stream（正确）
    assert "self.client.beta.messages.stream" in source, (
        "应该使用 self.client.beta.messages.stream 来支持 Citations"
    )

    # 验证 documents 通过 extra_body 传递
    assert 'kwargs["extra_body"] = {"documents": documents}' in source, (
        "documents 应该通过 extra_body 传递"
    )

    # 验证代码包含正确的注释说明
    assert "Citations API 是 beta 功能" in source or "beta 功能" in source, (
        "应该有注释说明这是 beta 功能"
    )
