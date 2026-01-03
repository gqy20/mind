"""引用显示功能

提供 Citations 引用列表的格式化显示。
"""

from mind.agents.utils import console


def _deduplicate_citations(citations: list[dict]) -> list[dict]:
    """对引用列表进行去重

    相同的文档标题和引用文本（前100字符）只保留首次出现的记录。

    Args:
        citations: 引用信息列表

    Returns:
        去重后的引用列表，保持原始顺序
    """
    unique_citations = []
    seen = set()

    for citation in citations:
        key = (
            citation.get("document_title", ""),
            citation.get("cited_text", "")[:100],
        )
        if key not in seen:
            seen.add(key)
            unique_citations.append(citation)

    return unique_citations


def format_citations(citations: list[dict]) -> list[str]:
    """格式化引用列表为文本行

    Args:
        citations: 引用信息列表

    Returns:
        格式化后的文本行列表（纯文本，不含 Rich 标记）
    """
    if not citations:
        return []

    # 使用提取的去重函数
    unique_citations = _deduplicate_citations(citations)

    lines: list[str] = []
    lines.append("")  # 空行
    lines.append("─" * 72)  # 分隔线
    lines.append("📚 引用来源：")

    for i, citation in enumerate(unique_citations, 1):
        title = citation.get("document_title", "未知来源")
        cited_text = citation.get("cited_text", "")

        # 限制引用文本长度
        if len(cited_text) > 150:
            cited_text = cited_text[:147] + "..."

        lines.append(f"[{i}] {title}")
        if cited_text:
            lines.append(f"    {cited_text}")

    lines.append("")  # 空行
    return lines


def display_citations(citations: list[dict]) -> None:
    """显示引用列表

    Args:
        citations: 引用信息列表
    """
    if not citations:
        return

    # 使用提取的去重函数
    unique_citations = _deduplicate_citations(citations)

    # 使用 Rich 格式化输出
    console.print()
    console.print(f"[dim]─ {'─' * 70}[/dim]")  # 分隔线
    console.print("[cyan]📚 引用来源：[/cyan]")

    for i, citation in enumerate(unique_citations, 1):
        title = citation.get("document_title", "未知来源")
        cited_text = citation.get("cited_text", "")

        # 限制引用文本长度
        if len(cited_text) > 150:
            cited_text = cited_text[:147] + "..."

        console.print(f"[dim][{i}][/dim] [yellow]{title}[/yellow]")
        if cited_text:
            console.print(f"    [dim]{cited_text}[/dim]")

    console.print()
