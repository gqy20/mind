"""
MCP 服务器定义

定义各种 MCP 服务器：
- 知识库服务器：对话历史语义搜索
- 代码分析服务器：代码库分析
- 网络搜索服务器：网络搜索集成
"""

from typing import Any

from mcp.server import Server

from mind.logger import get_logger

logger = get_logger("mind.mcp_servers")


# ============================================================================
# 知识库 MCP 服务器
# ============================================================================


def create_knowledge_mcp_server() -> dict[str, Any]:
    """创建知识库 MCP 服务器

    提供：
    - 对话历史搜索
    - 语义搜索（未来）
    - 摘要生成

    Returns:
        MCP 服务器配置字典
    """
    from pathlib import Path

    server = Server("knowledge-mcp")

    @server.tool()  # type: ignore[attr-defined]  # type: ignore[attr-defined]
    async def search_history(query: str, max_results: int = 5) -> str:
        """搜索对话历史

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果摘要
        """
        try:
            # 查找最新的搜索历史文件
            history_dir = Path("history")
            if not history_dir.exists():
                return "没有找到历史记录"

            history_files = sorted(
                history_dir.glob("search_history_*.json"),
                reverse=True,
            )

            if not history_files:
                return "没有找到搜索历史"

            # 使用最新的文件
            from mind.search_history import SearchHistory

            search_history = SearchHistory(file_path=history_files[0])

            # 搜索匹配的记录
            all_results = search_history.search_history(query)
            results = all_results[:max_results]

            if not results:
                return f"未找到与 '{query}' 相关的记录"

            # 格式化结果
            output = [f"找到 {len(results)} 条相关记录:\n"]
            for i, entry in enumerate(results[:max_results], 1):
                output.append(f"{i}. {entry.get('query', '未知')}")
                if entry.get("results"):
                    output.append(f"   {len(entry['results'])} 个结果")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"搜索历史失败: {e}")
            return f"搜索失败: {e}"

    @server.tool()  # type: ignore[attr-defined]
    async def get_recent_topics(count: int = 5) -> str:
        """获取最近的对话主题

        Args:
            count: 返回的主题数量

        Returns:
            最近的对话主题列表
        """
        try:
            history_dir = Path("history")
            if not history_dir.exists():
                return "没有找到历史记录"

            # 获取最近的对话文件（排除搜索历史）
            conv_files = sorted(
                [
                    f
                    for f in history_dir.glob("*.json")
                    if not f.name.startswith("search_history")
                ],
                reverse=True,
            )[:count]

            if not conv_files:
                return "没有找到对话记录"

            import json

            output = [f"最近的 {len(conv_files)} 个对话:\n"]
            for i, filepath in enumerate(conv_files[:count], 1):
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                topic = data.get("topic", "未知主题")
                timestamp = data.get("start_time", filepath.stem)
                output.append(f"{i}. {topic}")
                output.append(f"   时间: {timestamp}")
                output.append(f"   轮次: {data.get('turn_count', 0)}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            logger.error(f"获取最近主题失败: {e}")
            return f"获取失败: {e}"

    return {
        "type": "sdk",
        "name": "knowledge-mcp",
        "instance": server,
    }


# ============================================================================
# 代码分析 MCP 服务器
# ============================================================================


def create_code_analysis_mcp_server() -> dict[str, Any]:
    """创建代码分析 MCP 服务器

    提供：
    - 文件读取
    - 代码搜索
    - 代码库结构分析

    Returns:
        MCP 服务器配置字典
    """

    server = Server("code-analysis-mcp")

    @server.tool()  # type: ignore[attr-defined]
    async def read_file(file_path: str) -> str:
        """读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            文件内容
        """
        try:
            from pathlib import Path

            path = Path(file_path)
            if not path.exists():
                return f"文件不存在: {file_path}"

            # 安全检查：限制读取范围
            if not str(path.resolve()).startswith(str(Path.cwd().resolve())):
                return "错误：只能读取项目目录内的文件"

            content = path.read_text(encoding="utf-8")
            # 限制返回长度
            if len(content) > 5000:
                content = content[:5000] + "\n... (内容已截断)"

            return content

        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return f"读取失败: {e}"

    @server.tool()  # type: ignore[attr-defined]
    async def search_code(
        pattern: str,
        file_pattern: str = "*.py",
    ) -> str:
        """搜索代码

        Args:
            pattern: 搜索模式（正则表达式）
            file_pattern: 文件模式（例如 *.py）

        Returns:
            搜索结果
        """
        try:
            import re
            from pathlib import Path

            regex = re.compile(pattern)
            results = []

            # 搜索匹配的文件
            for filepath in Path(".").rglob(file_pattern):
                # 跳过虚拟环境和构建目录
                if any(
                    x in str(filepath)
                    for x in [".venv", "venv", "__pycache__", ".tox", "build"]
                ):
                    continue

                try:
                    content = filepath.read_text(encoding="utf-8")
                    matches = regex.findall(content)
                    if matches:
                        results.append(f"{filepath}: {len(matches)} 个匹配")
                except Exception:
                    continue

            if not results:
                return f"未找到匹配 '{pattern}' 的代码"

            return "\n".join(results[:20])  # 限制结果数量

        except Exception as e:
            logger.error(f"搜索代码失败: {e}")
            return f"搜索失败: {e}"

    @server.tool()  # type: ignore[attr-defined]
    async def list_structure(path: str = ".") -> str:
        """列出目录结构

        Args:
            path: 目录路径

        Returns:
            目录结构
        """
        try:
            from pathlib import Path

            base_path = Path(path)
            if not base_path.exists():
                return f"目录不存在: {path}"

            # 限制输出深度
            output = []
            for item in sorted(base_path.iterdir())[:50]:
                if item.is_dir():
                    output.append(f"📁 {item.name}/")
                else:
                    output.append(f"📄 {item.name}")

            return "\n".join(output) if output else "空目录"

        except Exception as e:
            logger.error(f"列出目录结构失败: {e}")
            return f"列出失败: {e}"

    return {
        "type": "sdk",
        "name": "code-analysis-mcp",
        "instance": server,
    }


# ============================================================================
# 网络搜索 MCP 服务器
# ============================================================================


def create_web_search_mcp_server() -> dict[str, Any]:
    """创建网络搜索 MCP 服务器

    提供网络搜索功能，扩展现有的 search_tool

    Returns:
        MCP 服务器配置字典
    """

    server = Server("web-search-mcp")

    @server.tool()  # type: ignore[attr-defined]
    async def search_web(query: str, max_results: int = 3) -> str:
        """网络搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果摘要
        """
        try:
            # 复用现有的搜索工具
            from mind.tools.search_tool import search_web

            results = await search_web(query, max_results=max_results)

            if not results:
                return f"未找到与 '{query}' 相关的搜索结果"

            return f"搜索结果:\n{results}"

        except Exception as e:
            logger.error(f"网络搜索失败: {e}")
            return f"搜索失败: {e}"

    return {
        "type": "sdk",
        "name": "web-search-mcp",
        "instance": server,
    }


# ============================================================================
# 自定义 MCP 服务器工厂
# ============================================================================


def create_custom_mcp_server(
    name: str,
    tools: list,
) -> dict[str, Any]:
    """创建自定义 MCP 服务器

    Args:
        name: 服务器名称
        tools: 工具函数列表

    Returns:
        MCP 服务器配置字典

    Example:
        >>> def my_tool(arg: str) -> str:
        ...     return f"处理: {arg}"
        >>> server = create_custom_mcp_server("my-server", [my_tool])
    """

    server = Server(name)

    for tool_func in tools:
        server.tool()(tool_func)  # type: ignore[attr-defined]

    return {
        "type": "sdk",
        "name": name,
        "instance": server,
    }
