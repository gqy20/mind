"""
智能体模块 - 定义单个对话智能体
"""

import asyncio
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import MessageParam
from rich.console import Console

from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.tools import ToolAgent

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

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
        tool_agent: "ToolAgent | None" = None,
    ):
        """初始化智能体

        Args:
            name: 智能体名称
            system_prompt: 系统提示词
            model: 使用的模型，默认从环境变量 ANTHROPIC_MODEL 读取
            tool_agent: 可选的工具智能体，用于代码分析等功能

        Raises:
            ValueError: 当名称为空时抛出异常
        """
        if not name or not name.strip():
            raise ValueError("名称不能为空")
        self.name = name
        self.model = model or DEFAULT_MODEL
        self.tool_agent = tool_agent

        # 如果有工具，自动在 system_prompt 中添加工具使用说明
        self.system_prompt = self._enhance_prompt_with_tool_instruction(system_prompt)
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
        logger.info(f"智能体初始化: {self.name}, 模型: {self.model}")

    def _enhance_prompt_with_tool_instruction(self, prompt: str) -> str:
        """增强提示词，添加工具使用说明

        Args:
            prompt: 原始提示词

        Returns:
            增强后的提示词（如果需要）
        """
        # 如果没有工具，直接返回原提示词
        if self.tool_agent is None:
            return prompt

        # 检查是否已包含工具说明（避免重复添加）
        # 检查常见的关键词
        tool_keywords = ["工具使用", "## 工具", "工具功能", "可用工具"]
        for keyword in tool_keywords:
            if keyword in prompt:
                # 已有工具说明，直接返回
                return prompt

        # 添加工具使用说明
        tool_instruction = """

## 工具使用

你配备了代码库分析工具，可以：
- 分析代码库结构和内容
- 读取特定文件的内容
- 搜索代码中的关键词

系统会在适当的时机自动调用工具，并将结果提供给你。你可以基于这些工具返回的信息进行更深入的分析和讨论。
"""
        return prompt + tool_instruction

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

    async def query_tool(
        self, question: str, messages: list[MessageParam] | None = None
    ) -> str | None:
        """分析对话上下文，提取关键信息

        Args:
            question: 查询问题（如"总结当前对话"、"提取主要观点"）
            messages: 对话历史记录

        Returns:
            对话摘要，如果对话为空或分析失败则返回 None
        """
        # 空对话返回 None
        if not messages:
            logger.debug(f"智能体 {self.name} 对话历史为空")
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
                logger.debug(f"智能体 {self.name} 没有有效对话内容")
                return None

            # 构建摘要
            summary_parts = []

            # 1. 话题概述
            if user_topics:
                first_topic = user_topics[0][:100]  # 限制长度
                summary_parts.append(f"**对话话题**: {first_topic}")

            # 2. 对话统计
            summary_parts.append(f"**对话轮次**: {len(assistant_responses)} 轮交流")

            # 3. 最近的观点（取最后 3 条，如果有的话）
            if assistant_responses:
                recent_responses = assistant_responses[-3:]
                summary_parts.append("\n**主要观点**:")
                for i, resp in enumerate(recent_responses, 1):
                    # 截取前 150 字符
                    short_resp = resp[:150] + "..." if len(resp) > 150 else resp
                    summary_parts.append(f"  {i}. {short_resp}")

            result = "\n".join(summary_parts)
            logger.info(f"智能体 {self.name} 对话分析完成，摘要长度: {len(result)}")
            return result

        except Exception as e:
            # 捕获所有异常，返回 None
            logger.error(f"智能体 {self.name} 对话分析异常: {e}", exc_info=True)
            return None
