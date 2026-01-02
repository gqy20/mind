"""
对话总结智能体模块

专门用于总结对话的轻量级智能体。
"""

import asyncio
import os
from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.prompts import SettingsConfig


# 默认模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

logger = get_logger("mind.summarizer")


class SummarizerAgent:
    """对话总结智能体

    轻量级智能体，专门用于总结对话。
    特点：
    - 无工具（无搜索、无代码分析）
    - 专注于总结任务
    - 只读对话历史
    """

    def __init__(
        self,
        model: str | None = None,
        settings: "SettingsConfig | None" = None,
    ):
        """初始化总结智能体

        Args:
            model: 使用的模型，默认从环境变量 ANTHROPIC_MODEL 读取
            settings: 系统设置配置（预留，目前未使用）
        """
        self.model = model or DEFAULT_MODEL
        self.name = "总结助手"

        # 显式读取 API key 并传递给客户端
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")

        # 支持 base_url（用于代理等场景）
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = AsyncAnthropic(api_key=api_key)

        # 系统提示词
        self.system_prompt = self._get_system_prompt()

        logger.info(f"总结智能体初始化完成, 模型: {self.model}")

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return (
            "你是一个专业的对话总结助手。你的任务是对两个智能体"
            "（支持者和挑战者）的对话进行准确、简洁的总结。\n\n"
            "## 总结要求\n\n"
            "1. **核心观点总结**：提取支持者的主要论点和立场\n"
            "2. **反对观点总结**：提取挑战者的主要质疑和反例\n"
            "3. **关键共识点**：双方达成一致的地方\n"
            "4. **主要分歧点**：双方仍有争议的地方\n\n"
            "## 格式要求（严格遵守）\n\n"
            "- 使用简洁、清晰的语言\n"
            "- 总结不超过 300 字\n"
            "- 使用项目符号列表组织内容\n"
            "- 客观中立，不偏袒任何一方\n"
            "- **确保每个字符只出现一次，不要重复字符或词语**\n"
            "- **使用标准的 markdown 格式**：\n"
            "  - 标题用 `##` 开头\n"
            "  - 列表项用 `- ` 开头\n"
            "  - 加粗用 `**文本**` 格式\n\n"
            "## 注意事项\n\n"
            "- 只基于提供的对话内容进行总结\n"
            "- 不要添加对话中没有的信息\n"
            "- 不要进行搜索或查询外部信息\n"
            "- 专注于提炼核心内容，避免冗余\n\n"
            "请直接输出总结内容，不要添加任何前缀或开场白。"
        )

    async def summarize(
        self, messages: list[MessageParam], topic: str, interrupt: asyncio.Event
    ) -> str:
        """总结对话

        Args:
            messages: 对话消息历史
            topic: 对话主题
            interrupt: 中断事件

        Returns:
            对话总结文本
        """
        # 构建对话预览（最近 20 条）
        content_preview_parts = []
        for msg in messages[-20:]:
            if isinstance(msg["content"], str):
                preview = msg["content"][:150]
            else:
                preview = str(msg["content"])[:150]
            content_preview_parts.append(f"- {msg['role']}: {preview}...")
        content_preview = "\n".join(content_preview_parts)

        # 构建总结提示词
        summary_prompt = f"""请对以下对话进行总结：

## 对话主题
{topic}

## 对话内容（最近 20 条消息）
{content_preview}

请按照要求提供：
1. 核心观点总结（支持者的主要论点）
2. 反对观点总结（挑战者的主要论点）
3. 关键共识点
4. 主要分歧点

总结不超过 300 字。"""

        # 构建消息
        messages_for_summary: list[MessageParam] = [
            {"role": "user", "content": summary_prompt}
        ]

        try:
            # 调用 API 生成总结
            response_text = ""

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages_for_summary,
            ) as stream:
                async for event in stream:
                    # 检查中断
                    if interrupt.is_set():
                        logger.debug("总结生成被中断")
                        return "对话总结被中断"

                    # 处理文本增量
                    if event.type == "content_block_delta":
                        if hasattr(event, "delta") and hasattr(event.delta, "type"):
                            if event.delta.type == "text_delta":
                                text = getattr(event.delta, "text", "")
                                response_text += text
                                print(text, end="", flush=True)

                    # 处理旧格式文本事件
                    elif event.type == "text":
                        text = getattr(event, "text", "")
                        response_text += text
                        print(text, end="", flush=True)

            summary = response_text.strip() or "对话总结生成失败"
            logger.info(f"对话总结已生成: {len(summary)} 字")
            return summary

        except Exception as e:
            logger.exception(f"总结生成失败: {e}")
            return f"对话总结生成失败: {e}"
