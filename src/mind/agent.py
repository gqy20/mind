"""
智能体模块 - 定义单个对话智能体

此模块保留用于向后兼容。
实际实现已迁移到 mind.agents 模块。
"""

# 重新导出新的 Agent 类和常量
from mind.agents.agent import DEFAULT_MODEL, Agent

__all__ = ["Agent", "DEFAULT_MODEL"]
