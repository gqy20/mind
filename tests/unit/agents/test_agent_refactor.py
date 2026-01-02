"""测试重构后的 Agent 类"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_agent_uses_new_components():
    """测试 Agent 使用新组件"""
    from mind.agents.agent import Agent

    # 使用 mock 来避免实际 API 调用
    with patch("mind.agents.client.os.getenv", return_value="test-key"):
        agent = Agent(
            name="测试智能体",
            system_prompt="你是一个测试助手",
            model="claude-sonnet-4-5-20250929",
        )

        # 验证组件存在
        assert agent.client is not None
        assert agent.documents is not None
        assert agent.response_handler is not None


@pytest.mark.asyncio
async def test_agent_respond_delegates_to_handler():
    """测试 Agent.respond 委托给 ResponseHandler"""
    from mind.agents.agent import Agent
    from mind.agents.response import ResponseResult

    with patch("mind.agents.client.os.getenv", return_value="test-key"):
        agent = Agent(
            name="测试智能体",
            system_prompt="你是一个测试助手",
        )

        # Mock ResponseHandler 返回 ResponseResult
        mock_result = ResponseResult(
            text="Mocked response", citations=[], citations_lines=[]
        )
        agent.response_handler.respond = AsyncMock(return_value=mock_result)

        result = await agent.respond(
            messages=[{"role": "user", "content": "Hi"}],
            interrupt=asyncio.Event(),
        )

        assert result == "Mocked response"


@pytest.mark.asyncio
async def test_agent_add_document_delegates():
    """测试 Agent.add_document 委托给 DocumentPool"""
    from mind.agents.agent import Agent

    with patch("mind.agents.client.os.getenv", return_value="test-key"):
        agent = Agent(
            name="测试智能体",
            system_prompt="你是一个测试助手",
        )

        doc = {"type": "document", "title": "test"}
        agent.add_document(doc)

        assert len(agent.documents.documents) == 1
        assert agent.documents.documents[0] == doc
