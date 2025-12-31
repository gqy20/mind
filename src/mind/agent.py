"""
智能体模块 - 定义单个对话智能体
"""

import asyncio
import os
from dataclasses import dataclass

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import MessageParam
from rich.console import Console

from mind.logger import get_logger

console = Console()
logger = get_logger("mind.agent")

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
        # 显式读取 API key 并传递给客户端
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 环境变量未设置")
        self.client = AsyncAnthropic(api_key=api_key)
        logger.info(f"智能体初始化: {self.name}, 模型: {self.model}")

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
            logger.debug(f"智能体 {self.name} 响应被中断")
            return None

        response_text = ""
        logger.debug(f"智能体 {self.name} 开始响应，历史消息数: {len(messages)}")

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
                        logger.debug(f"智能体 {self.name} 响应中途被中断")
                        return None

                    if event.type == "text":
                        response_text += event.text
                        # 实时打印
                        print(event.text, end="", flush=True)
                    elif event.type == "content_block_stop":
                        pass

        except APIStatusError as e:
            # API 状态错误（401, 429, 500 等）
            status_code = e.response.status_code if hasattr(e, "response") else 0
            error_msg = str(e)
            logger.error(f"API 状态错误: {status_code}, 消息: {error_msg}")

            if status_code == 401:
                console.print("\n[red]❌ 认证失败：API Key 无效或已过期[/red]")
                console.print("[yellow]请检查 ANTHROPIC_API_KEY 环境变量[/yellow]")
            elif status_code == 429:
                console.print("\n[yellow]⚠️速率限制：请求过于频繁，请稍后重试[/yellow]")
            elif status_code >= 500:
                console.print(f"\n[red]❌ API 错误 ({status_code})：服务器错误[/red]")
            else:
                console.print(f"\n[red]❌ API 错误 ({status_code})：{error_msg}[/red]")

            return None

        except TimeoutError:
            logger.error(f"请求超时: {self.name}")
            console.print("\n[red]❌ 请求超时：网络连接超时，请检查网络设置[/red]")
            return None

        except OSError as e:
            logger.error(f"网络错误: {self.name}, 错误: {e}")
            console.print(f"\n[red]❌ 网络错误：{e}[/red]")
            return None

        except Exception as e:
            logger.exception(f"未知错误: {self.name}, 错误: {e}")
            console.print(f"\n[red]❌ 未知错误：{e}[/red]")
            return None

        logger.debug(f"智能体 {self.name} 响应完成，长度: {len(response_text)}")
        return response_text
