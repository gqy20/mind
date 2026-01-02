"""
Agent query_tool 重构的单元测试

重构目标：从分析项目源码改为分析对话上下文
- query_tool 应该接收 messages 参数
- 分析对话历史中的关键观点
- 返回对话摘要而非项目结构
"""

import pytest
from anthropic.types import MessageParam

from mind.agent import Agent


class TestQueryToolWithContext:
    """测试 query_tool 分析对话上下文"""

    def test_query_tool_requires_messages_parameter(self):
        """测试：query_tool 需要 messages 参数"""
        # Arrange & Act & Assert - 检查方法签名
        import inspect

        sig = inspect.signature(Agent.query_tool)
        params = list(sig.parameters.keys())

        # 应该有 self, question, messages 三个参数
        assert "messages" in params, "query_tool 应该有 messages 参数"

    @pytest.mark.asyncio
    async def test_query_tool_analyzes_conversation_history(self):
        """测试：query_tool 分析对话历史"""
        # Arrange - 使用真实的 Agent 而不是 mock
        agent = Agent(name="测试", system_prompt="你是助手")

        # 创建真实的 messages
        messages: list[MessageParam] = [
            {"role": "user", "content": "话题：AI 是否有意识？"},
            {
                "role": "assistant",
                "content": "[支持者]: 我认为 AI 没有意识，只是模式匹配。",
            },
            {
                "role": "assistant",
                "content": "[挑战者]: 但图灵测试表明 AI 可以表现出意识。",
            },
        ]

        # Act - 调用分析对话上下文
        result = await agent.query_tool("分析当前对话", messages)

        # Assert - 应该返回对话摘要
        assert result is not None
        assert "支持者" in result or "挑战者" in result
        assert "意识" in result or "AI" in result

    @pytest.mark.asyncio
    async def test_query_tool_returns_none_with_empty_messages(self):
        """测试：空对话历史时返回 None"""
        # Arrange - 使用真实的 Agent 而不是 mock
        agent = Agent(name="测试", system_prompt="你是助手")

        messages: list[MessageParam] = []

        # Act
        result = await agent.query_tool("分析对话", messages)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_query_tool_extracts_key_viewpoints(self):
        """测试：提取对话中的关键观点"""
        # Arrange - 使用真实的 Agent 而不是 mock
        agent = Agent(name="测试", system_prompt="你是助手")

        messages: list[MessageParam] = [
            {"role": "user", "content": "讨论开源软件的商业模式"},
            {
                "role": "assistant",
                "content": "观点1：开源可以通过支持服务盈利",
            },
            {
                "role": "assistant",
                "content": "观点2：双许可模式也是可行方案",
            },
        ]

        # Act
        result = await agent.query_tool("总结观点", messages)

        # Assert - 应该包含关键信息
        assert result is not None
        assert any(keyword in result for keyword in ["开源", "商业模式", "观点"])
