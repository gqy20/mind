"""测试 flow.py 搜索结果处理方法的提取

测试从 _execute_search_interactive 和 _execute_ai_requested_search 中
提取的公共搜索结果处理逻辑。
"""

# 配置日志捕获
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

logging.basicConfig(level=logging.INFO)


@pytest.mark.asyncio
async def test_process_search_result_with_valid_result(flow_controller):
    """测试处理有效的搜索结果

    Given: 搜索返回有效结果
    When: 调用 _process_search_result
    Then: 结果被添加到消息历史和记忆
    """
    search_result = "这是搜索结果内容"

    # 调用方法
    await flow_controller._process_search_result(
        search_result=search_result,
        log_prefix="测试搜索",
    )

    # 验证消息被添加
    assert len(flow_controller.manager.messages) == 1
    message = flow_controller.manager.messages[0]
    assert message["role"] == "user"
    assert "网络搜索结果" in message["content"]
    assert search_result in message["content"]

    # 验证记忆被更新
    flow_controller.manager.memory.add_message.assert_called_once()


@pytest.mark.asyncio
async def test_process_search_result_with_empty_result(flow_controller):
    """测试处理空的搜索结果

    Given: 搜索返回空结果
    When: 调用 _process_search_result
    Then: 不添加消息，但记录警告日志
    """
    search_result = ""

    # 调用方法
    await flow_controller._process_search_result(
        search_result=search_result,
        log_prefix="测试搜索",
    )

    # 验证没有消息被添加（空结果不添加到历史）
    assert len(flow_controller.manager.messages) == 0


@pytest.mark.asyncio
async def test_process_search_result_memory_update(flow_controller):
    """测试搜索结果处理更新记忆

    Given: 搜索返回结果
    When: 调用 _process_search_result
    Then: 记忆被正确更新
    """
    search_result = "测试结果"

    await flow_controller._process_search_result(
        search_result=search_result,
        log_prefix="测试搜索",
    )

    # 验证记忆被更新
    flow_controller.manager.memory.add_message.assert_called_once()
    call_args = flow_controller.manager.memory.add_message.call_args
    assert call_args[0][0] == "user"  # role
    assert "网络搜索结果" in call_args[0][1]  # content


@pytest.mark.asyncio
async def test_execute_search_interactive_uses_extracted_method(
    flow_controller, mock_manager
):
    """测试交互式搜索使用提取的结果处理方法

    Given: 有搜索结果
    When: 调用 _execute_search_interactive
    Then: 内部调用 _process_search_result
    """
    with patch(
        "mind.tools.search_tool.search_web", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = "搜索结果"

        # 监控 _process_search_result 方法
        process_result_spy = AsyncMock(wraps=flow_controller._process_search_result)
        flow_controller._process_search_result = process_result_spy

        # 执行搜索
        await flow_controller._execute_search_interactive("测试查询")

        # 验证 _process_search_result 被调用
        process_result_spy.assert_called_once_with(
            search_result="搜索结果",
            log_prefix=f"第 {mock_manager.turn} 轮网络搜索",
        )


@pytest.mark.asyncio
async def test_execute_ai_requested_search_uses_extracted_method(flow_controller):
    """测试 AI 请求搜索使用提取的结果处理方法

    Given: 有搜索结果
    When: 调用 _execute_ai_requested_search
    Then: 内部调用 _process_search_result
    """
    mock_agent = MagicMock()
    mock_agent.name = "Supporter"

    with patch(
        "mind.tools.search_tool.search_web", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = "AI 搜索结果"

        # 监控 _process_search_result 方法
        process_result_spy = AsyncMock(wraps=flow_controller._process_search_result)
        flow_controller._process_search_result = process_result_spy

        # 执行搜索
        await flow_controller._execute_ai_requested_search(mock_agent, "AI查询")

        # 验证 _process_search_result 被调用
        process_result_spy.assert_called_once_with(
            search_result="AI 搜索结果",
            log_prefix="AI 请求的搜索",
        )
