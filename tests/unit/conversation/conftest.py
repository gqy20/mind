"""Conversation 测试模块的共享 Fixtures

提供跨多个测试文件共享的 pytest fixtures。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mind.conversation import FlowController


@pytest.fixture
def mock_manager():
    """创建模拟的 ConversationManager

    提供 FlowController 测试所需的模拟 manager 实例。
    包含基本的属性设置，可根据需要在测试中覆盖。

    Returns:
        MagicMock: 模拟的 ConversationManager 实例
    """
    manager = MagicMock()
    manager.turn = 5
    manager.current = 0
    manager.is_running = True
    manager.messages = []
    manager.memory = MagicMock()
    manager.memory.add_message = MagicMock()
    manager.memory.get_status = MagicMock(return_value="green")
    manager.memory._total_tokens = 1000
    manager.memory.config.max_context = 10000
    manager.agent_a = MagicMock()
    manager.agent_a.name = "Supporter"
    manager.agent_a.query_tool = AsyncMock()
    manager.agent_b = MagicMock()
    manager.agent_b.name = "Challenger"
    manager.enable_tools = False
    manager.tool_interval = 0
    manager.interrupt = MagicMock()
    manager.interrupt.is_set = MagicMock(return_value=False)
    manager.end_detector = MagicMock()
    manager.end_detector.detect = MagicMock(return_value=MagicMock(detected=False))
    return manager


@pytest.fixture
def flow_controller(mock_manager):
    """创建 FlowController 实例

    使用 mock_manager 创建 FlowController 实例用于测试。

    Args:
        mock_manager: 注入的模拟 ConversationManager

    Returns:
        FlowController: FlowController 实例
    """
    controller = FlowController(mock_manager)
    return controller
