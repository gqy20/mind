"""测试过渡期死循环 bug

测试在过渡期间，如果智能体持续返回结束标记，
不会导致 pending_end_count 被反复重置而陷入死循环。
"""

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_transition_period_should_not_reset_pending_count():
    """测试过渡期不应重复设置 pending_end_count

    场景：
    1. 第 1 轮：智能体 A 响应包含 END 标记，触发过渡期（pending_end_count=2）
    2. 第 2 轮：智能体 B 响应也包含 END 标记，但不应重置 pending_end_count
    3. 第 3 轮：过渡期应该结束，pending_end_count 应递减到 0

    This test will FAIL with the current bug.
    """
    from mind.conversation.flow import FlowController

    # 准备 (Arrange)
    manager = MagicMock()
    manager.topic = "测试主题"
    manager.start_time = None
    manager.messages = []
    manager.memory = MagicMock()
    manager.memory._total_tokens = 1000
    manager.memory.config.max_context = 200000  # 添加这个配置
    manager.memory.get_status = MagicMock(return_value="green")
    manager.is_running = True
    manager.turn = 0
    manager.current = 0
    manager.agent_a = MagicMock()
    manager.agent_b = MagicMock()
    manager.agent_a.name = "Supporter"
    manager.agent_b.name = "Challenger"
    manager.interrupt = asyncio.Event()
    manager.enable_tools = False
    manager.search_interval = 0
    manager.pending_end_count = 0  # 初始无过渡期
    manager._pending_end_active = False

    # 模拟智能体响应（每轮都包含 END 标记）
    async def mock_respond_with_end_marker(messages, interrupt):
        return "这是我的观点 <!-- END -->"

    manager.agent_a.respond = mock_respond_with_end_marker
    manager.agent_b.respond = mock_respond_with_end_marker

    # 模拟结束检测器（每次都返回 transition=2）
    manager.end_detector = MagicMock()

    async def mock_detect_async(*args, **kwargs):
        result = MagicMock()
        result.detected = True
        result.method = "marker_verified"
        result.reason = "对话充分展开"
        result.transition = 2  # 需要 2 轮过渡
        result.analysis_score = 85
        return result

    manager.end_detector.detect_async = mock_detect_async

    # 模拟总结功能
    async def mock_summarize(*args, **kwargs):
        return "对话总结"

    manager._summarize_conversation = mock_summarize
    manager.save_conversation = MagicMock()

    # 执行 (Act)
    controller = FlowController(manager)
    controller._is_interactive = False  # 非交互模式

    # 模拟执行对话，直到 is_running 变为 False（最多 10 轮防止死循环）
    max_rounds = 10
    rounds_executed = 0
    for i in range(max_rounds):
        await controller._turn()
        rounds_executed += 1
        if not manager.is_running:
            break

    # 断言 (Assert)
    # 预期行为：
    # - 第 1 轮：设置 pending_end_count = 2，然后递减到 1
    # - 第 2 轮：跳过结束检测，保持 1，然后递减到 0
    # - 第 2 轮末尾：过渡期结束，对话应该自动终止
    # - pending_end_count 最终应该是 0
    assert manager.pending_end_count == 0, (
        f"过渡期结束后 pending_end_count 应该是 0，"
        f"但实际是 {manager.pending_end_count}。"
        f"执行了 {rounds_executed} 轮。"
        f"这表明在过渡期中，pending_end_count 被反复重置了。"
    )


@pytest.mark.asyncio
async def test_transition_count_should_only_be_set_once():
    """测试 pending_end_count 应该只在首次检测到结束时设置

    场景：验证即使多次检测到结束标记，pending_end_count 也只设置一次
    """
    from mind.conversation.flow import FlowController

    # 准备 (Arrange)
    manager = MagicMock()
    manager.topic = "测试"
    manager.start_time = None
    manager.messages = []
    manager.memory = MagicMock()
    manager.memory._total_tokens = 1000
    manager.memory.config.max_context = 200000  # 添加这个配置
    manager.memory.get_status = MagicMock(return_value="green")
    manager.is_running = True
    manager.turn = 0
    manager.current = 0
    manager.agent_a = MagicMock()
    manager.agent_b = MagicMock()
    manager.agent_a.name = "A"
    manager.agent_b.name = "B"
    manager.interrupt = asyncio.Event()
    manager.enable_tools = False
    manager.search_interval = 0
    manager.pending_end_count = 0
    manager._pending_end_active = False

    async def mock_respond(messages, interrupt):
        return "响应 <!-- END -->"

    manager.agent_a.respond = mock_respond
    manager.agent_b.respond = mock_respond

    # 记录 pending_end_count 被设置的次数
    set_count = 0
    original_pending_count = 0

    def track_pending_count(value):
        nonlocal set_count, original_pending_count
        if value != original_pending_count:
            set_count += 1
            original_pending_count = value

    # 模拟结束检测器
    manager.end_detector = MagicMock()

    async def mock_detect_async(*args, **kwargs):
        result = MagicMock()
        result.detected = True
        result.transition = 2
        result.method = "marker"
        result.reason = ""
        result.analysis_score = 80
        return result

    manager.end_detector.detect_async = mock_detect_async

    # 模拟总结功能
    async def mock_summarize(*args, **kwargs):
        return "总结"

    manager._summarize_conversation = mock_summarize
    manager.save_conversation = MagicMock()

    # 执行 (Act)
    controller = FlowController(manager)
    controller._is_interactive = False

    # 执行 4 轮
    for _ in range(4):
        await controller._turn()

    # 断言 (Assert)
    # pending_end_count 应该只被设置一次（第 1 轮），后续轮次不应重置
    # 当前 bug：每轮都会重置
    assert manager.pending_end_count == 0, "4 轮后过渡期应该已结束"
