"""工具函数

提供智能体使用的工具函数。
"""

import re

from rich.console import Console

from mind.logger import get_logger

# 已知的智能体名称列表，用于清理角色名前缀
KNOWN_AGENTS = ["支持者", "挑战者"]

# Rich Console 实例
console = Console()

# 日志器
logger = get_logger("mind.agents.utils")


def _clean_agent_name_prefix(text: str) -> str:
    """清理文本开头的智能体角色名前缀

    清理任意已知的智能体角色名前缀，如 "[支持者]: " 或 "[挑战者]: "。
    这样可以防止 AI 错误地生成对方的角色名。

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    # 首先尝试清理已知的智能体角色名
    for agent_name in KNOWN_AGENTS:
        prefix = f"[{agent_name}]:"
        if text.startswith(prefix):
            return text[len(prefix) :].lstrip()

        # 也检查不带方括号的格式
        prefix_plain = f"{agent_name}:"
        if text.startswith(prefix_plain):
            return text[len(prefix_plain) :].lstrip()

    # 如果没有匹配到已知角色名，使用正则表达式清理任意 [xxx]: 格式
    # 但要小心不要清理类似 [1] 这样的引用标记
    # 使用负向后顾断言，确保 [xxx]: 中的 xxx 不是纯数字
    text = re.sub(r"^\[([^\d][^\]]*)\]:\s*", "", text)

    return text
