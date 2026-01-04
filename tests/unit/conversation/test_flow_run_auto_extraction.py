"""测试 flow.py run_auto() 方法提取的子函数

测试从 run_auto() 中提取的各个子功能函数。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_initialize_conversation_topic(flow_controller, mock_manager):
    """测试初始化对话主题

    Given: 对话主题
    When: 调用 _initialize_conversation
    Then: 主题消息被添加到对话历史
    """
    topic = "人工智能的未来"

    await flow_controller._initialize_conversation(topic)

    # 验证主题和开始时间被设置
    assert mock_manager.topic == topic
    assert mock_manager.start_time is not None

    # 验证主题消息被添加
    assert len(mock_manager.messages) == 1
    assert mock_manager.messages[0]["role"] == "user"
    assert "人工智能的未来" in mock_manager.messages[0]["content"]


@pytest.mark.asyncio
async def test_process_agent_turn_with_response(flow_controller, mock_manager):
    """测试处理智能体轮次（有响应）

    Given: 智能体返回有效响应
    When: 调用 _process_agent_turn
    Then: 轮次标记和响应被添加到历史，返回输出行
    """
    mock_manager.agent_a.respond = AsyncMock(return_value="这是响应内容")

    output_lines, should_end = await flow_controller._process_agent_turn(
        mock_manager.agent_a
    )

    # 验证返回输出行
    assert len(output_lines) > 0
    assert any("Supporter" in line for line in output_lines)
    assert "这是响应内容" in "\n".join(output_lines)
    assert should_end is False

    # 验证消息被添加到历史（轮次标记 + 响应 = 2 条）
    assert len(mock_manager.messages) == 2
    # 第一条是轮次标记（mock_manager.turn 初始值是 5，所以是轮次 6）
    assert mock_manager.messages[0]["role"] == "user"
    assert "[轮次 6]" in mock_manager.messages[0]["content"]
    assert "Supporter" in mock_manager.messages[0]["content"]
    # 第二条是响应
    assert mock_manager.messages[1]["role"] == "assistant"
    assert mock_manager.messages[1]["content"] == "这是响应内容"


@pytest.mark.asyncio
async def test_process_agent_turn_interrupted(flow_controller, mock_manager):
    """测试处理智能体轮次（被中断）

    Given: 智能体返回 None（被中断）
    When: 调用 _process_agent_turn
    Then: 返回空列表，轮次标记已添加
    """
    mock_manager.agent_a.respond = AsyncMock(return_value=None)

    output_lines, should_end = await flow_controller._process_agent_turn(
        mock_manager.agent_a
    )

    # 验证返回空列表
    assert output_lines == []
    assert should_end is False

    # 验证轮次标记已添加（即使被中断，轮次标记也已添加）
    assert len(mock_manager.messages) == 1
    assert mock_manager.messages[0]["role"] == "user"
    assert "[轮次 6]" in mock_manager.messages[0]["content"]


@pytest.mark.asyncio
async def test_process_agent_turn_with_citations(flow_controller, mock_manager):
    """测试处理带引用的智能体响应

    Given: 智能体响应包含引用
    When: 调用 _process_agent_turn
    Then: 引用行被添加到输出
    """
    mock_manager.agent_a.respond = AsyncMock(return_value="响应内容")
    mock_manager.agent_a._last_citations_lines = ["📚 引用来源:", "[1] 测试文档"]

    output_lines, _ = await flow_controller._process_agent_turn(mock_manager.agent_a)

    # 验证引用行在输出中
    output_text = "\n".join(output_lines)
    assert "引用来源" in output_text
    assert "测试文档" in output_text


@pytest.mark.asyncio
async def test_process_agent_turn_with_ending_request(flow_controller, mock_manager):
    """测试处理智能体请求结束对话

    Given: 智能体响应包含结束标记
    When: 调用 _process_agent_turn
    Then: 返回包含结束标记的输出，设置 should_end 标志
    """
    mock_manager.agent_a.respond = AsyncMock(return_value="响应内容 <!-- END -->")
    mock_manager.end_detector.detect = MagicMock(return_value=MagicMock(detected=True))

    output_lines, should_end = await flow_controller._process_agent_turn(
        mock_manager.agent_a
    )

    # 验证返回包含结束标记
    assert should_end is True
    assert any("结束对话" in line for line in output_lines)


@pytest.mark.asyncio
async def test_format_conversation_output(flow_controller):
    """测试格式化对话输出

    Given: 对话主题和总结
    When: 调用 _format_conversation_output
    Then: 返回格式化的输出行
    """
    output_lines = flow_controller._format_conversation_output(
        topic="测试主题",
        summary="这是总结内容",
        turn_count=10,
        token_count=5000,
    )

    # 验证输出包含必要元素（注意：主题不在 _format_conversation_output 中）
    output_text = "\n".join(output_lines)
    assert "对话总结" in output_text
    assert "这是总结内容" in output_text
    assert "统计" in output_text
    assert "10 轮对话" in output_text
    assert "5000 tokens" in output_text


@pytest.mark.asyncio
async def test_check_memory_trim_needed(flow_controller, mock_manager):
    """测试检查是否需要清理记忆

    Given: 记忆状态为 red
    When: 调用 _check_memory_trim_needed
    Then: 返回 True 并增加 trim_count
    """
    mock_manager.memory.get_status = MagicMock(return_value="red")
    mock_manager._trim_count = 0
    mock_manager.should_exit_after_trim = MagicMock(return_value=False)

    should_exit = await flow_controller._check_memory_trim_needed()

    # 验证 trim_count 被增加
    assert mock_manager._trim_count == 1
    # 验证检查是否应该退出
    assert should_exit is False


@pytest.mark.asyncio
async def test_initialize_output_header(flow_controller):
    """测试初始化输出头部

    Given: 对话主题
    When: 调用 _initialize_output_header
    Then: 返回格式化的头部行
    """
    output_lines = flow_controller._initialize_output_header("测试主题")

    # 验证头部格式
    assert len(output_lines) == 4
    assert "测试主题" in output_lines[0]
    assert output_lines[1] == ""
    assert output_lines[2] == "---"
    assert output_lines[3] == ""
