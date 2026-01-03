"""对话分析功能

提供对话上下文分析和信息提取功能。
"""

from typing import TYPE_CHECKING

from anthropic.types import MessageParam

from mind.logger import get_logger

if TYPE_CHECKING:
    pass

# 日志器
logger = get_logger("mind.agents.conversation_analyzer")


def analyze_conversation(
    messages: list[MessageParam], max_recent: int = 3
) -> str | None:
    """分析对话上下文，提取关键信息

    Args:
        messages: 对话历史记录
        max_recent: 保留最近的回复数量

    Returns:
        对话摘要，如果对话为空或分析失败则返回 None
    """
    # 空对话返回 None
    if not messages:
        logger.debug("对话历史为空")
        return None

    try:
        # 提取对话内容
        conversation_parts = []
        user_topics = []
        assistant_responses = []

        for msg in messages:
            # 使用显式类型注解避免 mypy 类型窄化
            role: str = msg.get("role", "")
            content = msg.get("content", "")

            # 跳过系统消息和空内容
            if role == "system" or not content:
                continue

            # 处理不同类型的内容
            if isinstance(content, str):
                text = content
            else:
                # 处理结构化内容（blocks）
                text = str(content)

            conversation_parts.append(text)

            # 收集用户话题和助手回复
            if role == "user":
                # 提取话题（去除前缀）
                clean_text = text.strip()
                if clean_text:
                    user_topics.append(clean_text)
            elif role == "assistant":
                clean_text = text.strip()
                if clean_text:
                    assistant_responses.append(clean_text)

        # 如果没有有效对话内容，返回 None
        if not conversation_parts:
            logger.debug("没有有效对话内容")
            return None

        # 构建摘要
        summary_parts = []

        # 1. 话题概述
        if user_topics:
            first_topic = user_topics[0][:100]  # 限制长度
            summary_parts.append(f"**对话话题**: {first_topic}")

        # 2. 对话统计
        summary_parts.append(f"**对话轮次**: {len(assistant_responses)} 轮交流")

        # 3. 最近的观点（取最后 N 条，如果有的话）
        if assistant_responses:
            recent_responses = assistant_responses[-max_recent:]
            summary_parts.append("\n**主要观点**:")
            for i, resp in enumerate(recent_responses, 1):
                # 截取前 150 字符
                short_resp = resp[:150] + "..." if len(resp) > 150 else resp
                summary_parts.append(f"  {i}. {short_resp}")

        result = "\n".join(summary_parts)
        logger.info(f"对话分析完成，摘要长度: {len(result)}")
        return result

    except Exception as e:
        # 捕获所有异常，返回 None
        logger.error(f"对话分析异常: {e}", exc_info=True)
        return None


class ConversationAnalyzer:
    """对话分析器"""

    def __init__(self, max_recent: int = 3):
        """初始化对话分析器

        Args:
            max_recent: 保留最近的回复数量
        """
        self.max_recent = max_recent

    def analyze(self, messages: list[MessageParam]) -> str | None:
        """分析对话上下文

        Args:
            messages: 对话历史记录

        Returns:
            对话摘要
        """
        return analyze_conversation(messages, max_recent=self.max_recent)
