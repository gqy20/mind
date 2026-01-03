"""对话管理模块 - 协调两个智能体的对话

这个模块被拆分为多个子模块，每个模块负责一个特定的功能域。
"""

from mind.conversation.ending import EndingHandler
from mind.conversation.ending_detector import (
    ConversationEndConfig,
    ConversationEndDetector,
    EndProposal,
)
from mind.conversation.flow import FlowController
from mind.conversation.interaction import InteractionHandler
from mind.conversation.search_handler import SearchHandler

__all__ = [
    "SearchHandler",
    "InteractionHandler",
    "EndingHandler",
    "FlowController",
    "ConversationEndDetector",
    "ConversationEndConfig",
    "EndProposal",
]
