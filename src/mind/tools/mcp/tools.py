"""
MCP 工具注册

提供工具装饰器和注册功能
"""

from collections.abc import Callable
from functools import wraps

from mcp.server import Server

from mind.logger import get_logger

logger = get_logger("mind.mcp_tools")


# 工具注册表
_tool_registry: dict[str, list[str]] = {}


def register_tool(server: Server) -> Callable:
    """注册工具到 MCP 服务器的装饰器

    Args:
        server: MCP 服务器实例

    Returns:
        工具装饰器

    Example:
        >>> server = Server("my-server")
        >>> @register_tool(server)
        ... async def my_tool(arg: str) -> str:
        ...     return f"处理: {arg}"
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # 注册到服务器
        server.tool()(wrapper)  # type: ignore[attr-defined]

        # 记录到注册表
        server_name = getattr(server, "name", "unknown")
        if server_name not in _tool_registry:
            _tool_registry[server_name] = []
        _tool_registry[server_name].append(func.__name__)

        logger.debug(f"工具已注册: {server_name}.{func.__name__}")
        return wrapper

    return decorator


def mcp_tool(name: str | None = None, description: str = "") -> Callable:
    """MCP 工具装饰器（简化版）

    Args:
        name: 工具名称
        description: 工具描述

    Returns:
        装饰器函数

    Example:
        >>> @mcp_tool(name="search", description="搜索知识库")
        ... async def search_knowledge(query: str) -> str:
        ...     return f"搜索结果: {query}"
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # 动态添加属性（用于运行时元数据）
        wrapper._mcp_tool_name = name or func.__name__  # type: ignore[attr-defined]
        wrapper._mcp_tool_description = description  # type: ignore[attr-defined]

        return wrapper

    return decorator


def get_registered_tools(server_name: str) -> list[str]:
    """获取已注册的工具列表

    Args:
        server_name: 服务器名称

    Returns:
        工具名称列表
    """
    return _tool_registry.get(server_name, []).copy()
