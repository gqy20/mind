"""
工具扩展层 - 基于 claude-agent-sdk

提供以下功能：
- 文件操作、代码分析
- 搜索历史管理
- Hook 回调实现
"""

from mind.tools.hooks import ToolHooks
from mind.tools.tool_agent import ToolAgent

__all__ = ["ToolAgent", "ToolHooks"]
