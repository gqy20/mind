"""对话管理模块 - 协调两个智能体的对话

这个模块被拆分为多个子模块，每个模块负责一个特定的功能域。
"""

__all__ = [
    # ConversationManager 已移至 manager.py，请通过 mind.manager 导入
    "SearchHandler",
    "InteractionHandler",
    "EndingHandler",
    "FlowController",
    # 对话结束检测
    "ConversationEndDetector",
    "ConversationEndConfig",
    "EndProposal",
]


def __getattr__(name: str):
    """延迟导入模块，避免循环导入

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    # 导入路径映射
    _imports = {
        "SearchHandler": ("mind.conversation.search_handler", "SearchHandler"),
        "InteractionHandler": ("mind.conversation.interaction", "InteractionHandler"),
        "EndingHandler": ("mind.conversation.ending", "EndingHandler"),
        "FlowController": ("mind.conversation.flow", "FlowController"),
        # 对话结束检测
        "ConversationEndDetector": (
            "mind.conversation.ending_detector",
            "ConversationEndDetector",
        ),
        "ConversationEndConfig": (
            "mind.conversation.ending_detector",
            "ConversationEndConfig",
        ),
        "EndProposal": ("mind.conversation.ending_detector", "EndProposal"),
    }

    if name in _imports:
        module_path, attr_name = _imports[name]
        from importlib import import_module

        module = import_module(module_path)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
