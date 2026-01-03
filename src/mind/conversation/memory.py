"""
记忆管理模块 - 基于 Token 监控的对话历史管理

提供智能的对话历史管理：
- Token 精确计数和监控
- 分阶段状态判断（green/yellow/red）
- 自动清理策略（从后往前保留）
- 边界保护（最少保留最近 N 轮）
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class TokenConfig:
    """Token 配置"""

    max_context: int = 150_000  # 上限：预留 50k 给响应
    warning_threshold: int = 120_000  # 警告：开始准备清理
    target_after_trim: int = 80_000  # 清理后目标：留出增长空间
    min_keep_recent: int = 10  # 最少保留最近轮数
    max_trim_count: int = 3  # 最大清理次数，达到后自动退出并总结


class MemoryManager:
    """基于 Token 监控的记忆管理器"""

    def __init__(self, config: TokenConfig | None = None):
        """初始化记忆管理器

        Args:
            config: Token 配置，默认使用默认配置
        """
        self.config = config or TokenConfig()
        self._total_tokens = 0
        self._message_tokens: list[int] = []  # 每条消息的 token 数

    def add_message(self, role: str, content: str) -> dict:
        """添加消息并更新 token 计数

        Args:
            role: 消息角色（user/assistant）
            content: 消息内容

        Returns:
            消息字典
        """
        tokens = self._count_tokens(content)
        message = {"role": role, "content": content}

        self._message_tokens.append(tokens)
        self._total_tokens += tokens

        return message

    def should_trim(self) -> bool:
        """判断是否需要清理

        Returns:
            是否需要清理
        """
        return self._total_tokens >= self.config.max_context

    def get_status(self) -> Literal["green", "yellow", "red"]:
        """获取当前状态

        Returns:
            状态：green（安全）、yellow（警告）、red（超限）
        """
        if self._total_tokens < self.config.warning_threshold:
            return "green"
        elif self._total_tokens < self.config.max_context:
            return "yellow"
        return "red"

    def trim_messages(self, messages: list[dict]) -> list[dict]:
        """清理消息，返回清理后的列表

        Args:
            messages: 消息列表

        Returns:
            清理后的消息列表
        """
        if not self.should_trim():
            return messages

        if not messages:
            return []

        # 策略：从后往前保留，直到达到目标 token 数
        result: list[dict] = []
        accumulated = 0

        # 至少保留最近的 min_keep_recent 轮
        min_idx = max(0, len(messages) - self.config.min_keep_recent)
        recent_messages = messages[min_idx:]
        recent_tokens = self._message_tokens[min_idx:]

        for msg, tokens in zip(reversed(recent_messages), reversed(recent_tokens)):
            result.insert(0, msg)
            accumulated += tokens

        # 继续添加更早的消息，直到达到目标
        if min_idx > 0:
            older_messages = messages[:min_idx]
            older_tokens = self._message_tokens[:min_idx]

            for msg, tokens in zip(reversed(older_messages), reversed(older_tokens)):
                if accumulated + tokens > self.config.target_after_trim:
                    break
                result.insert(0, msg)
                accumulated += tokens

        # 更新计数
        self._message_tokens = [self._count_tokens(m["content"]) for m in result]
        self._total_tokens = accumulated

        return result

    def _count_tokens(self, text: str) -> int:
        """估算 token 数（Claude 约为 4 字符/token）

        Args:
            text: 文本内容

        Returns:
            估算的 token 数
        """
        return len(text) // 4
