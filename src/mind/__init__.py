"""Mind - AI agents that collaborate to spark innovation"""

__version__ = "0.1.0"

from .agents.agent import Agent

__all__ = [
    "__version__",
    "Agent",
    "ConversationManager",
    "SummarizerAgent",
]


def __getattr__(name: str):
    """懒加载，避免循环导入

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    if name == "ConversationManager":
        from .conversation import ConversationManager

        return ConversationManager
    if name == "SummarizerAgent":
        from .agents.summarizer import SummarizerAgent

        return SummarizerAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
