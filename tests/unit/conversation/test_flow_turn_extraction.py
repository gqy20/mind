"""测试 flow.py _turn() 方法提取的子函数

测试从 _turn() 中提取的各个子功能函数。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_check_and_execute_tools_with_tool_result(flow_controller, mock_manager):
    """测试检查并执行工具调用（有结果）

    Given: 工具启用且满足触发条件
    When: 调用 _check_and_execute_tools
    Then: 工具被调用，结果被添加到历史
    """
    # 设置工具相关属性
    mock_manager.enable_tools = True
    mock_manager.tool_interval = 3
    mock_manager.turn = 3

    await flow_controller._check_and_execute_tools(mock_manager.agent_a)

    # 验证工具被调用
    mock_manager.agent_a.query_tool.assert_called_once_with(
        "总结当前对话", mock_manager.messages
    )

    # 验证工具结果被添加到历史
    assert len(mock_manager.messages) == 1
    assert "上下文更新" in mock_manager.messages[0]["content"]


@pytest.mark.asyncio
async def test_check_and_execute_tools_no_trigger(flow_controller, mock_manager):
    """测试工具调用不触发条件

    Given: 轮次不满足工具触发条件
    When: 调用 _check_and_execute_tools
    Then: 工具不被调用
    """
    mock_manager.turn = 1  # 不满足 tool_interval 条件

    await flow_controller._check_and_execute_tools(mock_manager.agent_a)

    # 验证工具未被调用
    mock_manager.agent_a.query_tool.assert_not_called()

    # 验证没有消息被添加
    assert len(mock_manager.messages) == 0


@pytest.mark.asyncio
async def test_execute_agent_response_with_search_request(
    flow_controller, mock_manager
):
    """测试执行智能体响应（包含搜索请求）

    Given: 智能体响应包含搜索请求
    When: 调用 _execute_agent_response
    Then: 搜索被执行，返回最终响应
    """
    # 第一次响应包含搜索请求
    mock_manager.agent_a.respond = AsyncMock(
        side_effect=[
            "让我搜索一下 [搜索: 人工智能]",
            "搜索后的响应",
        ]
    )
    # mock search_handler (它是 flow_controller 的属性)
    flow_controller.search_handler.has_search_request = MagicMock(return_value=True)
    flow_controller.search_handler.extract_search_from_response = MagicMock(
        return_value="人工智能"
    )

    response = await flow_controller._execute_agent_response(
        mock_manager.agent_a, monitor_input=False
    )

    # 验证返回最终响应
    assert response == "搜索后的响应"


@pytest.mark.asyncio
async def test_execute_agent_response_interrupted(flow_controller, mock_manager):
    """测试执行智能体响应（被中断）

    Given: 智能体返回 None
    When: 调用 _execute_agent_response
    Then: 返回 None
    """
    mock_manager.agent_a.respond = AsyncMock(return_value=None)

    response = await flow_controller._execute_agent_response(
        mock_manager.agent_a, monitor_input=False
    )

    # 验证返回 None
    assert response is None


@pytest.mark.asyncio
async def test_add_agent_message_to_history(flow_controller, mock_manager):
    """测试添加智能体消息到历史

    Given: 智能体和响应内容
    When: 调用 _add_agent_message
    Then: 消息被格式化并添加到历史
    """
    response_content = "这是响应内容"

    flow_controller._add_agent_message(
        mock_manager.agent_a, response_content, to_memory=True
    )

    # 验证消息被添加
    assert len(mock_manager.messages) == 1
    assert mock_manager.messages[0]["role"] == "assistant"
    assert "Supporter" in mock_manager.messages[0]["content"]
    assert "这是响应内容" in mock_manager.messages[0]["content"]

    # 验证记忆被更新
    mock_manager.memory.add_message.assert_called_once()

    # 验证轮次增加
    assert mock_manager.turn == 6


@pytest.mark.asyncio
async def test_add_agent_message_skips_memory(flow_controller, mock_manager):
    """测试添加智能体消息（不更新记忆）

    Given: to_memory=False
    When: 调用 _add_agent_message
    Then: 消息被添加但记忆不更新
    """
    response_content = "响应内容"

    flow_controller._add_agent_message(
        mock_manager.agent_a, response_content, to_memory=False
    )

    # 验证记忆未被更新
    mock_manager.memory.add_message.assert_not_called()


@pytest.mark.asyncio
async def test_handle_ai_search_request(flow_controller, mock_manager):
    """测试处理 AI 搜索请求

    Given: 响应包含搜索请求
    When: 调用 _handle_ai_search_request
    Then: 搜索被执行，返回新响应
    """
    # mock search_handler (它是 flow_controller 的属性)
    flow_controller.search_handler.has_search_request = MagicMock(return_value=True)
    flow_controller.search_handler.extract_search_from_response = MagicMock(
        return_value="AI搜索"
    )

    # 直接 mock 方法
    mock_search = AsyncMock()
    flow_controller._execute_ai_requested_search = mock_search

    mock_respond = AsyncMock(return_value="新响应")
    mock_manager.agent_a.respond = mock_respond

    response = await flow_controller._handle_ai_search_request(
        mock_manager.agent_a, "原始响应"
    )

    # 验证搜索被执行
    mock_search.assert_called_once_with(mock_manager.agent_a, "AI搜索")

    # 验证返回新响应
    assert response == "新响应"


@pytest.mark.asyncio
async def test_handle_ai_search_request_no_search(flow_controller, mock_manager):
    """测试处理 AI 搜索请求（无搜索请求）

    Given: 响应不包含搜索请求
    When: 调用 _handle_ai_search_request
    Then: 返回原始响应
    """
    # mock search_handler (它是 flow_controller 的属性)
    flow_controller.search_handler.has_search_request = MagicMock(return_value=False)

    response = await flow_controller._handle_ai_search_request(
        mock_manager.agent_a, "原始响应"
    )

    # 验证返回原始响应
    assert response == "原始响应"
