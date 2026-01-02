"""对话管理模块 - 协调两个智能体的对话

这个模块被拆分为多个子模块，每个模块负责一个特定的功能域。
"""

__all__ = ["ConversationManager", "ProgressDisplay", "SearchHandler"]


def __getattr__(name: str):
    """延迟导入模块，避免循环导入

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    if name == "ConversationManager":
        from mind.conversation import manager

        return manager.ConversationManager
    elif name == "ProgressDisplay":
        from mind.conversation import progress

        return progress.ProgressDisplay
    elif name == "SearchHandler":
        from mind.conversation import search_handler

        return search_handler.SearchHandler
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
