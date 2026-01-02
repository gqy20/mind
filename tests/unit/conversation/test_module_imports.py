"""测试 conversation 子模块的导入

确保拆分后的模块结构可以正常导入和使用。
"""

import pytest


def test_conversation_manager_can_be_imported():
    """测试 ConversationManager 可以从新位置导入"""
    # 这个测试将在实现后通过
    with pytest.raises(ImportError):
        from mind.conversation import ConversationManager

        assert ConversationManager is not None


def test_progress_display_can_be_imported():
    """测试 ProgressDisplay 可以导入"""
    from mind.conversation.progress import ProgressDisplay

    assert ProgressDisplay is not None


def test_search_handler_can_be_imported():
    """测试 SearchHandler 可以导入"""
    from mind.conversation.search_handler import SearchHandler

    assert SearchHandler is not None


def test_interaction_handler_can_be_imported():
    """测试 InteractionHandler 可以导入"""
    from mind.conversation.interaction import InteractionHandler

    assert InteractionHandler is not None


def test_ending_handler_can_be_imported():
    """测试 EndingHandler 可以导入"""
    with pytest.raises(ImportError):
        from mind.conversation.ending import EndingHandler

        assert EndingHandler is not None


def test_flow_controller_can_be_imported():
    """测试 FlowController 可以导入"""
    with pytest.raises(ImportError):
        from mind.conversation.flow import FlowController

        assert FlowController is not None
