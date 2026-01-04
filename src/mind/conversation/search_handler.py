"""搜索处理模块

提供搜索关键词提取、搜索请求检测和触发条件判断功能。
"""

import re

from mind.logger import get_logger

logger = get_logger("mind.conversation.search_handler")

# 搜索请求标记模式
_SEARCH_REQUEST_PATTERN = re.compile(r"\[搜索:\s*([^\]]+)\]")


class SearchHandler:
    """搜索处理器类

    负责从对话历史中提取搜索关键词、检测搜索请求和判断触发条件。

    Attributes:
        manager: ConversationManager 实例的引用
    """

    def __init__(self, manager):
        """初始化搜索处理器

        Args:
            manager: ConversationManager 实例，用于访问对话状态
        """
        self.manager = manager

    def extract_search_query(self) -> str | None:
        """从对话历史中提取搜索关键词

        Returns:
            搜索关键词，如果无法提取返回 None
        """
        # 优先使用最近的用户消息
        if self.manager.messages:
            for msg in reversed(self.manager.messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str) and content.strip():
                        clean_query = content.strip()

                        # 移除系统消息（轮次标记）
                        if clean_query.startswith("现在由 ") and " 发言" in clean_query:
                            continue

                        # 移除工具分析结果（上下文更新等）
                        if clean_query.startswith(
                            "[上下文更新]"
                        ) or clean_query.startswith("[系统消息"):
                            continue

                        # 移除常见的命令前缀
                        for prefix in ["/quit", "/exit", "/clear"]:
                            if clean_query.startswith(prefix):
                                clean_query = ""
                                break

                        if clean_query:
                            # 限制关键词长度
                            return clean_query[:100]

            # 从最近的助手回复中提取关键词
            for msg in reversed(self.manager.messages):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        # 简单提取：取前几个有意义的词
                        words = content.strip().split()[:5]
                        if words:
                            return " ".join(words)[:100]

        # 如果没有用户消息，使用对话主题
        if self.manager.topic:
            return self.manager.topic[:100]  # type: ignore[no-any-return]

        return None

    def has_search_request(self, response: str) -> bool:
        """检测 AI 响应中是否包含搜索请求

        Args:
            response: AI 的响应文本

        Returns:
            是否包含搜索请求
        """
        if not response:
            return False
        return bool(_SEARCH_REQUEST_PATTERN.search(response))

    def extract_search_from_response(self, response: str) -> str | None:
        """从 AI 响应中提取搜索关键词

        Args:
            response: AI 的响应文本

        Returns:
            搜索关键词，如果没有找到返回 None
        """
        if not response:
            return None
        match = _SEARCH_REQUEST_PATTERN.search(response)
        return match.group(1).strip() if match else None

    def should_trigger_search(self, last_response: str | None = None) -> bool:
        """判断是否应该触发搜索

        触发条件（按优先级）：
        1. AI 主动请求（使用 [搜索: 关键词] 语法）
        2. 固定间隔（作为兜底）

        AI 通过提示词指导何时使用搜索功能，而不是硬编码规则。

        Args:
            last_response: 最近的 AI 响应（用于检测主动请求）

        Returns:
            是否应该触发搜索
        """
        # 1. 检查 AI 是否主动请求
        if last_response and self.has_search_request(last_response):
            logger.info("AI 主动请求搜索")
            return True

        # 2. 固定间隔兜底（仅在启用搜索时）
        if (
            self.manager.enable_search
            and self.manager.search_interval > 0
            and self.manager.turn > 0
            and self.manager.turn % self.manager.search_interval == 0
        ):
            logger.info(f"达到搜索间隔: 第 {self.manager.turn} 轮")
            return True

        return False
