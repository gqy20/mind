"""Citations 文档池管理

管理 Anthropic Citations API 的文档池。
"""

from typing import TYPE_CHECKING

from anthropic.types import MessageParam

if TYPE_CHECKING:
    from collections.abc import Sequence


class DocumentPool:
    """Citations 文档池"""

    def __init__(self, max_documents: int = 10, ttl: int = 5):
        """初始化文档池

        Args:
            max_documents: 最大文档数量
            ttl: 文档存活时间（轮数），0 表示不清理
        """
        self.max_documents = max_documents
        self.ttl = ttl
        self.documents: list[dict] = []

    def add(self, doc: dict) -> None:
        """添加文档到池

        超过最大数量时，移除最旧的文档。

        Args:
            doc: Citations API 格式的文档字典
        """
        if len(self.documents) >= self.max_documents:
            self.documents.pop(0)
        self.documents.append(doc)

    def merge_into_messages(self, messages: list[MessageParam]) -> list[MessageParam]:
        """将文档池中的文档合并到消息中

        Args:
            messages: 原始消息列表

        Returns:
            合并了文档的消息列表
        """
        if not self.documents:
            return messages

        formatted_messages: list[MessageParam] = []
        for msg in messages:
            if msg["role"] == "user":
                new_content = self._merge_content(msg.get("content", ""))
                formatted_messages.append(
                    MessageParam(role="user", content=new_content)  # type: ignore[typeddict-item]
                )
            else:
                formatted_messages.append(msg)

        return formatted_messages

    def _merge_content(self, content: object) -> "Sequence[object]":
        """将文档池与消息内容合并

        Args:
            content: 原始消息内容（字符串或结构化列表）

        Returns:
            合并后的内容列表
        """
        if isinstance(content, str):
            return [*self.documents, {"type": "text", "text": content}]
        elif isinstance(content, list):
            return list(self.documents) + list(content)
        else:
            return list(self.documents)

    @staticmethod
    def from_search_history(search_entries: list[dict]) -> dict:
        """将搜索历史记录转换为 Citations 文档

        Args:
            search_entries: 搜索记录列表（来自 SearchHistory）

        Returns:
            Citations API 文档格式的字典
        """
        content_blocks = []

        for entry in search_entries:
            query = entry.get("query", "未知查询")
            results = entry.get("results", [])

            if results:
                content_blocks.append({"type": "text", "text": f"\n## 搜索: {query}"})
                for result in results:
                    title = result.get("title", "无标题")
                    href = result.get("href", "")
                    body = result.get("body", "")

                    block_parts = [title]
                    if href:
                        block_parts.append(f"来源: {href}")
                    if body:
                        short_body = body[:200] + "..." if len(body) > 200 else body
                        block_parts.append(f"内容: {short_body}")

                    content_blocks.append(
                        {"type": "text", "text": "\n".join(block_parts)}
                    )

        return {
            "type": "document",
            "source": {
                "type": "content",
                "content": content_blocks,
            },
            "title": "搜索历史记录",
            "context": f"包含 {len(search_entries)} 次搜索结果",
            "citations": {"enabled": True},
        }

    def cleanup_old(self) -> None:
        """清理过期的文档

        根据 TTL（存活时间）移除超过保留轮次的文档。
        如果 TTL 为 0，则不清理。
        """
        if self.ttl == 0:
            return

        self.documents = [doc for doc in self.documents if doc.get("age", 0) < self.ttl]
