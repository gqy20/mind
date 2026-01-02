"""网络搜索工具模块

基于 ddgs 库实现网络搜索功能，为对话系统提供外部信息检索能力。
"""

import asyncio
from datetime import datetime
from functools import partial, wraps
from urllib.parse import urlparse

from ddgs import DDGS
from loguru import logger

# NSFW 域名黑名单（从实际对话中收集的问题域名）
NSFW_DOMAIN_BLOCKLIST = {
    "wiki.evaafly.cc",
    "brand.hinrijv.cc",
    "hwmrz2.cccgg49.com",
    "wiki.saostwdi.com",
    "cgw666.com",
    "ww.djteqdbi.org",
}


def _is_safe_domain(href: str) -> bool:
    """检查域名是否安全

    Args:
        href: URL 链接

    Returns:
        True 表示安全，False 表示在黑名单中
    """
    try:
        domain = urlparse(href).netloc.lower()
        # 移除端口号
        domain = domain.split(":")[0]
        return domain not in NSFW_DOMAIN_BLOCKLIST
    except Exception:
        return True  # 解析失败时默认安全


def _sync_wrapper(func):
    """将同步函数转换为异步函数"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        # 使用 partial 处理关键字参数
        func_with_args = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, func_with_args)

    return wrapper


@_sync_wrapper
def _search_sync(query: str, max_results: int) -> list[dict]:
    """同步执行网络搜索"""
    return DDGS().text(query, max_results=max_results)


def _format_result_as_block(result: dict) -> dict:
    """将单个搜索结果格式化为 Citations content block

    Args:
        result: 单个搜索结果字典

    Returns:
        Citations content block 格式的字典
    """
    title = result.get("title", "无标题")
    href = result.get("href", "")
    body = result.get("body", "")

    # 构建块文本
    block_parts = [title]
    if href:
        block_parts.append(f"来源: {href}")
    if body:
        # 限制摘要长度
        short_body = body[:200] + "..." if len(body) > 200 else body
        block_parts.append(f"内容: {short_body}")

    block_text = "\n".join(block_parts)
    return {"type": "text", "text": block_text}


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

        # 过滤 NSFW 域名
        filtered_results = []
        blocked_count = 0
        for r in results:
            href = r.get("href", "")
            if href and not _is_safe_domain(href):
                blocked_count += 1
                logger.debug(f"过滤不安全域名: {href}")
                continue
            filtered_results.append(r)

        if blocked_count > 0:
            logger.info(f"过滤了 {blocked_count} 个不安全域名")

        if not filtered_results:
            logger.warning(f"所有搜索结果都被过滤: {query}")
            return None

        # 格式化结果 - 使用引用标记格式
        summary_parts = [f"**网络搜索结果**: {query}\n"]
        summary_parts.append("请在回复时使用引用标记，例如：`根据研究[1]，...`\n")

        for i, r in enumerate(filtered_results[:max_results], 1):
            title = r.get("title", "无标题")
            href = r.get("href", "")
            body = r.get("body", "")

            summary_parts.append(f"[{i}] {title}")
            if href:
                summary_parts.append(f"    来源: {href}")
            if body:
                # 限制摘要长度
                short_body = body[:150] + "..." if len(body) > 150 else body
                summary_parts.append(f"    内容: {short_body}")
            summary_parts.append("")

        result = "\n".join(summary_parts)
        logger.info(f"搜索完成: {query}, 返回 {len(filtered_results)} 条结果")
        return result

    except Exception as e:
        logger.error(f"搜索失败: {query}, 错误: {e}")
        return None


async def search_web_as_document(query: str, max_results: int = 5) -> dict | None:
    """搜索网络并返回 Citations API 文档格式

    将搜索结果转换为 Anthropic Citations API 所需的 document 格式，
    支持精确定位引用。

    Args:
        query: 搜索查询字符串
        max_results: 最大结果数量，默认 5

    Returns:
        Citations API document 格式的字典，如果失败返回 None：
        {
            "type": "document",
            "source": {
                "type": "content",
                "content": [
                    {"type": "text", "text": "结果1"},
                    {"type": "text", "text": "结果2"}
                ]
            },
            "title": "搜索结果: {query}",
            "context": "搜索时间: ...",
            "citations": {"enabled": True}
        }
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

        # 过滤 NSFW 域名
        filtered_results = []
        blocked_count = 0
        for r in results:
            href = r.get("href", "")
            if href and not _is_safe_domain(href):
                blocked_count += 1
                logger.debug(f"过滤不安全域名: {href}")
                continue
            filtered_results.append(r)

        if blocked_count > 0:
            logger.info(f"过滤了 {blocked_count} 个不安全域名")

        if not filtered_results:
            logger.warning(f"所有搜索结果都被过滤: {query}")
            return None

        # 转换为 content blocks（每个搜索结果作为一个可引用的块）
        content_blocks = [
            _format_result_as_block(r) for r in filtered_results[:max_results]
        ]

        # 构建文档结构
        document = {
            "type": "document",
            "source": {"type": "content", "content": content_blocks},
            "title": f"搜索结果: {query}",
            "context": f"搜索时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "citations": {"enabled": True},
        }

        logger.info(f"搜索文档创建完成: {query}, {len(content_blocks)} 个内容块")
        return document

    except Exception as e:
        logger.error(f"搜索文档创建失败: {query}, 错误: {e}")
        return None
