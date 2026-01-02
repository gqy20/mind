"""对话管理模块 - 协调两个智能体的对话

这个模块被拆分为多个子模块，每个模块负责一个特定的功能域。
"""

# ConversationManager 已移至 manager.py，通过 mind.manager 导入
from mind.manager import ConversationManager  # noqa: F401

__all__ = [
    "ConversationManager",
    "ProgressDisplay",
    "SearchHandler",
    "InteractionHandler",
    "EndingHandler",
    "FlowController",
]


def __getattr__(name: str):
    """延迟导入模块，避免循环导入

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    if name == "ProgressDisplay":
        from mind.conversation import progress

        return progress.ProgressDisplay
    elif name == "SearchHandler":
        from mind.conversation import search_handler

        return search_handler.SearchHandler
    elif name == "InteractionHandler":
        from mind.conversation import interaction

        return interaction.InteractionHandler
    elif name == "EndingHandler":
        from mind.conversation import ending

        return ending.EndingHandler
    elif name == "FlowController":
        from mind.conversation import flow

        return flow.FlowController
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
