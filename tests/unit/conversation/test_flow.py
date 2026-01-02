"""测试 FlowController 对话流程控制功能

测试对话循环、自动运行和轮次执行逻辑。
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFlowController:
    """测试 FlowController 类"""

    def test_flow_controller_can_be_imported(self):
        """测试 FlowController 可以导入"""
        from mind.conversation.flow import FlowController

        assert FlowController is not None

    @pytest.mark.asyncio
    async def test_start_initializes_conversation(self):
        """测试 start 方法初始化对话"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.topic = None
        manager.start_time = None
        manager.messages = []
        manager.memory = MagicMock()
        manager.is_running = True
        manager.turn_interval = 0.5

        controller = FlowController(manager)

        # 模拟 _turn 方法
        controller._turn = AsyncMock()
        # 模拟用户没有输入
        controller.is_input_ready = MagicMock(return_value=False)
        # 模拟 KeyboardInterrupt 退出循环
        controller._turn.side_effect = [None, KeyboardInterrupt()]

        with patch("builtins.print"):
            await controller.start("测试主题")

        # 验证主题被设置
        assert manager.topic == "测试主题"
        # 验证消息被初始化
        assert len(manager.messages) > 0
        assert "测试主题" in manager.messages[0]["content"]

    @pytest.mark.asyncio
    async def test_run_auto_returns_output(self):
        """测试 run_auto 方法返回对话输出"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.topic = None
        manager.start_time = None
        manager.messages = []
        manager.memory = MagicMock()
        manager.memory._total_tokens = 1000
        manager.memory.get_status = MagicMock(return_value="green")
        manager.is_running = True
        manager.turn = 0
        manager.current = 0
        manager.agent_a = MagicMock()
        manager.agent_b = MagicMock()
        manager.agent_a.name = "AgentA"
        manager.agent_b.name = "AgentB"
        manager.interrupt = asyncio.Event()
        manager.enable_tools = False
        manager.search_interval = 0

        # 模拟 agent respond 返回结果
        async def mock_respond(messages, interrupt):
            return "测试响应"

        manager.agent_a.respond = mock_respond
        manager.agent_b.respond = mock_respond

        # 模拟 end_detector
        manager.end_detector = MagicMock()
        end_result = MagicMock()
        end_result.detected = False
        manager.end_detector.detect = MagicMock(return_value=end_result)

        controller = FlowController(manager)

        # 模拟 _should_trigger_search 返回 False
        controller.should_trigger_search = MagicMock(return_value=False)

        with patch("builtins.print"):
            result = await controller.run_auto("自动主题", max_turns=1)

        # 验证返回输出
        assert "自动主题" in result
        assert "测试响应" in result

    @pytest.mark.asyncio
    async def test_turn_executes_agent_response(self):
        """测试 _turn 方法执行智能体响应"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.current = 0
        manager.agent_a = MagicMock()
        manager.agent_a.name = "AgentA"
        manager.agent_b = MagicMock()
        manager.agent_b.name = "AgentB"
        manager.messages = []
        manager.memory = MagicMock()
        manager.memory.get_status = MagicMock(return_value="green")
        manager.memory._total_tokens = 1000
        manager.memory.config.max_context = 150000
        manager.turn = 0
        manager.enable_tools = False
        manager.search_interval = 0
        manager.is_running = True
        manager.interrupt = asyncio.Event()

        # 模拟 agent respond
        async def mock_respond(messages, interrupt):
            return "AI 响应内容"

        manager.agent_a.respond = mock_respond

        # 模拟 end_detector
        manager.end_detector = MagicMock()
        end_result = MagicMock()
        end_result.detected = False
        manager.end_detector.detect = MagicMock(return_value=end_result)

        # 模拟搜索检查
        manager._has_search_request = MagicMock(return_value=False)

        controller = FlowController(manager)

        # 模拟 should_trigger_search
        controller.should_trigger_search = MagicMock(return_value=False)

        with patch("builtins.print"):
            await controller._turn()

        # 验证消息被添加
        assert len(manager.messages) == 1
        # 验证轮次增加
        assert manager.turn == 1
        # 验证切换到下一个智能体
        assert manager.current == 1

    @pytest.mark.asyncio
    async def test_turn_handles_end_proposal(self):
        """测试 _turn 方法处理结束提议"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.current = 0
        manager.agent_a = MagicMock()
        manager.agent_a.name = "AgentA"
        manager.agent_b = MagicMock()
        manager.agent_b.name = "AgentB"
        manager.messages = []
        manager.memory = MagicMock()
        manager.memory.get_status = MagicMock(return_value="green")
        manager.memory._total_tokens = 1000
        manager.memory.config.max_context = 150000
        manager.turn = 0
        manager.enable_tools = False
        manager.search_interval = 0
        manager.is_running = True
        manager.interrupt = asyncio.Event()

        # 模拟 agent respond
        async def mock_respond(messages, interrupt):
            return "结束讨论 [END]"

        manager.agent_a.respond = mock_respond

        # 模拟 end_detector 检测到结束
        manager.end_detector = MagicMock()
        end_result = MagicMock()
        end_result.detected = True
        manager.end_detector.detect = MagicMock(return_value=end_result)

        # 模拟 _summarize_conversation
        async def mock_summarize():
            return "对话总结"

        manager._summarize_conversation = mock_summarize

        controller = FlowController(manager)

        # 模拟搜索检查
        controller.should_trigger_search = MagicMock(return_value=False)

        # Mock input 模拟用户确认结束（直接按 Enter）
        with patch("builtins.print"), patch("builtins.input", return_value=""):
            await controller._turn()

        # 验证对话被标记为结束
        assert not manager.is_running

    @pytest.mark.asyncio
    async def test_run_auto_stops_at_max_turns(self):
        """测试 run_auto 在达到最大轮数时停止"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.topic = None
        manager.start_time = None
        manager.messages = []
        manager.memory = MagicMock()
        manager.memory._total_tokens = 500
        manager.memory.get_status = MagicMock(return_value="green")
        manager.is_running = True
        manager.turn = 0
        manager.current = 0
        manager.agent_a = MagicMock()
        manager.agent_a.name = "AgentA"
        manager.agent_b = MagicMock()
        manager.agent_b.name = "AgentB"
        manager.interrupt = asyncio.Event()
        manager.enable_tools = False
        manager.search_interval = 0

        # 模拟 agent respond
        async def mock_respond(messages, interrupt):
            return "响应"

        manager.agent_a.respond = mock_respond
        manager.agent_b.respond = mock_respond

        # 模拟 end_detector
        manager.end_detector = MagicMock()
        end_result = MagicMock()
        end_result.detected = False
        manager.end_detector.detect = MagicMock(return_value=end_result)

        controller = FlowController(manager)
        controller.should_trigger_search = MagicMock(return_value=False)

        with patch("builtins.print"):
            result = await controller.run_auto("主题", max_turns=2)

        # 验证输出包含统计信息
        assert "轮对话" in result

    @pytest.mark.asyncio
    async def test_run_auto_handles_end_detection(self):
        """测试 run_auto 处理 AI 结束检测"""
        from mind.conversation.flow import FlowController

        manager = MagicMock()
        manager.topic = None
        manager.start_time = None
        manager.messages = []
        manager.memory = MagicMock()
        manager.memory._total_tokens = 500
        manager.memory.get_status = MagicMock(return_value="green")
        manager.is_running = True
        manager.turn = 0
        manager.current = 0
        manager.agent_a = MagicMock()
        manager.agent_a.name = "AgentA"
        manager.agent_b = MagicMock()
        manager.agent_b.name = "AgentB"
        manager.interrupt = asyncio.Event()
        manager.enable_tools = False
        manager.search_interval = 0

        # 模拟 agent respond 返回结束标记
        async def mock_respond(messages, interrupt):
            return "讨论完毕 [END]"

        manager.agent_a.respond = mock_respond
        manager.agent_b.respond = mock_respond

        # 模拟 end_detector 检测到结束
        manager.end_detector = MagicMock()
        end_result = MagicMock()
        end_result.detected = True
        manager.end_detector.detect = MagicMock(return_value=end_result)

        controller = FlowController(manager)
        controller.should_trigger_search = MagicMock(return_value=False)

        with patch("builtins.print"):
            result = await controller.run_auto("主题", max_turns=5)

        # 验证输出包含结束信息
        assert "AI 请求结束对话" in result
