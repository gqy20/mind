"""
MCP (Model Context Protocol) 工具集成

提供以下功能：
- MCP 服务器定义和注册
- 工具权限管理
"""

from mind.tools.mcp.servers import (
    create_code_analysis_mcp_server,
    create_knowledge_mcp_server,
    create_web_search_mcp_server,
)
from mind.tools.mcp.tools import register_tool

__all__ = [
    "create_knowledge_mcp_server",
    "create_code_analysis_mcp_server",
    "create_web_search_mcp_server",
    "register_tool",
]
