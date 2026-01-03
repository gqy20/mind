"""Mind - AI agents that collaborate to spark innovation"""

from mind.agents.agent import Agent
from mind.agents.summarizer import SummarizerAgent
from mind.manager import ConversationManager

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Agent",
    "ConversationManager",
    "SummarizerAgent",
]
