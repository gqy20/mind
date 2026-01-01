"""网络搜索工具模块

基于 ddgs 库实现网络搜索功能，为对话系统提供外部信息检索能力。
"""

import asyncio
from functools import wraps

from ddgs import DDGS
from loguru import logger


def _sync_wrapper(func):
    """将同步函数转换为异步函数"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    return wrapper


@_sync_wrapper
def _search_sync(query: str, max_results: int) -> list[dict]:
    """同步执行网络搜索"""
    return DDGS().text(query, max_results=max_results)


async def search_web(query: str, max_results: int = 5) -> str | None:
    """搜索网络并返回格式化的结果

    Args:
        query: 搜索查询字符串
        max_results: 最大结果数量，默认 5

    Returns:
        格式化的搜索结果文本，如果失败返回 None
    """
    # 处理空查询
    if not query or not query.strip():
        logger.warning("搜索查询为空")
        return None

    try:
        # 执行搜索
        results = await _search_sync(query, max_results)

        if not results:
            logger.warning(f"搜索未返回结果: {query}")
            return None

        # 格式化结果
        summary_parts = [f"**网络搜索结果**: {query}\n"]

        for i, r in enumerate(results[:max_results], 1):
            title = r.get("title", "无标题")
            href = r.get("href", "")
            body = r.get("body", "")

            summary_parts.append(f"{i}. {title}")
            if href:
                summary_parts.append(f"   链接: {href}")
            if body:
                # 限制摘要长度
                short_body = body[:100] + "..." if len(body) > 100 else body
                summary_parts.append(f"   摘要: {short_body}")
            summary_parts.append("")

        result = "\n".join(summary_parts)
        logger.info(f"搜索完成: {query}, 返回 {len(results)} 条结果")
        return result

    except Exception as e:
        logger.error(f"搜索失败: {query}, 错误: {e}")
        return None
