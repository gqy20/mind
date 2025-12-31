"""
智能体模块 - 定义单个对话智能体
"""

import asyncio
import os
from dataclasses import dataclass

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

# 默认模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")


@dataclass
class Agent:
    """对话智能体"""

    name: str
    system_prompt: str
    client: AsyncAnthropic

    def __init__(self, name: str, system_prompt: str, model: str | None = None):
        """初始化智能体

        Args:
            name: 智能体名称
            system_prompt: 系统提示词
            model: 使用的模型，默认从环境变量 ANTHROPIC_MODEL 读取

        Raises:
            ValueError: 当名称为空时抛出异常
        """
        if not name or not name.strip():
            raise ValueError("名称不能为空")
        self.name = name
        self.system_prompt = system_prompt
        self.model = model or DEFAULT_MODEL
        self.client = AsyncAnthropic()

    async def respond(
        self, messages: list[MessageParam], interrupt: asyncio.Event
    ) -> str | None:
        """流式响应，支持中断

        Args:
            messages: 对话历史
            interrupt: 中断事件，用户输入时触发

        Returns:
            完整响应文本，如果被中断则返回 None
        """
        # 如果立即被中断，直接返回 None
        if interrupt.is_set():
            return None

        response_text = ""

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
            ) as stream:
                async for event in stream:
                    # 检查中断
                    if interrupt.is_set():
                        return None

                    if event.type == "text":
                        response_text += event.text
                        # 实时打印
                        print(event.text, end="", flush=True)
                    elif event.type == "content_block_stop":
                        pass

        except Exception as e:
            # 错误时也打印
            print(f"\n[错误: {e}]")
            return None

        return response_text
