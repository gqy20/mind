"""工具函数

提供智能体使用的工具函数。
"""

from rich.console import Console

from mind.logger import get_logger

# Rich Console 实例
console = Console()

# 日志器
logger = get_logger("mind.agents.utils")
