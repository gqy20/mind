"""引用显示功能

提供 Citations 引用列表的格式化显示。
"""

from mind.agents.utils import console


def display_citations(citations: list[dict]) -> None:
    """显示引用列表

    Args:
        citations: 引用信息列表
    """
    if not citations:
        return

    # 去重（相同的文档标题和引用文本只显示一次）
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
