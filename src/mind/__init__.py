"""Mind - AI agents that collaborate to spark innovation"""

__version__ = "0.1.0"

from .agent import Agent
from .conversation import ConversationManager
from .summarizer import SummarizerAgent

__all__ = [
    "__version__",
    "Agent",
    "ConversationManager",
    "SummarizerAgent",
]
