"""Agents 模块

提供智能体相关的类和功能。
"""

from mind.agents.agent import Agent

__all__ = [
    "Agent",
    "SummarizerAgent",
]


def __getattr__(name: str):
    """延迟导入模块，避免循环导入

    Args:
        name: 要导入的名称

    Returns:
        导入的对象
    """
    if name == "SummarizerAgent":
        from mind.agents.summarizer import SummarizerAgent

        return SummarizerAgent
    if name == "ConversationAnalyzer":
        from mind.agents.conversation_analyzer import ConversationAnalyzer

        return ConversationAnalyzer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
