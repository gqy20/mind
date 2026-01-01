"""
智能体模块 - 定义单个对话智能体
"""

import asyncio
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import MessageParam, ToolParam
from rich.console import Console

from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.tools import ToolAgent


def _get_tools_schema() -> list[ToolParam]:
    """获取可用工具的 schema 定义

    Returns:
        工具 schema 列表，用于 Anthropic Tool Use API
    """
    return [
        ToolParam(
            name="search_web",
            description="搜索网络信息，获取最新数据、事实、定义等",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或问题",
                    }
                },
                "required": ["query"],
            },
        )
    ]


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
    search_documents: list
    max_documents: int
    document_ttl: int

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
        self.search_documents = []
        self.max_documents = 10
        self.document_ttl = 5

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
        """流式响应，支持中断和 Tool Use API

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
        tool_use_buffer: list[dict] | None = None

        logger.debug(f"智能体 {self.name} 开始响应，历史消息数: {len(messages)}")

        try:
            # 第一轮：生成响应（可能包含工具调用）
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                tools=_get_tools_schema(),  # 传入工具定义
            ) as stream:
                event_count = 0
                async for event in stream:
                    event_count += 1
                    # 每 50 个事件记录一次（避免日志过多）
                    if event_count % 50 == 0:
                        logger.debug(
                            f"已处理 {event_count} 个事件，最新事件类型: {event.type}"
                        )
                    # 检查中断
                    if interrupt.is_set():
                        logger.debug(f"智能体 {self.name} 响应中途被中断")
                        return None

                    if event.type == "text":
                        # 实时清理角色名前缀（如果 AI 误添加了）
                        text = event.text
                        # 移除常见的角色名前缀格式
                        if text.startswith(f"[{self.name}]:"):
                            text = text[len(f"[{self.name}]:") :].lstrip()
                        elif text.startswith(f"{self.name}:"):
                            text = text[len(f"{self.name}:") :].lstrip()

                        response_text += text
                        # 实时打印
                        print(text, end="", flush=True)

                    elif event.type == "content_block_stop":
                        # 在 content_block_stop 时，工具调用的 input 已完全构建
                        if hasattr(event, "content_block") and hasattr(
                            event.content_block, "type"
                        ):
                            if event.content_block.type == "tool_use":
                                logger.debug(
                                    f"检测到工具调用完成: {event.content_block.name}"
                                )
                                if tool_use_buffer is None:
                                    tool_use_buffer = []
                                tool_use_buffer.append(
                                    {
                                        "type": "tool_use",
                                        "id": getattr(event.content_block, "id", ""),
                                        "name": getattr(
                                            event.content_block, "name", ""
                                        ),
                                        "input": getattr(
                                            event.content_block, "input", {}
                                        ),
                                    }
                                )

            # 处理工具调用
            buffer_status = (
                f"{len(tool_use_buffer)} 个工具调用"
                if tool_use_buffer
                else "0 个工具调用"
            )
            logger.debug(f"工具调用检测完成，buffer 状态: {buffer_status}")
            if tool_use_buffer:
                for tool_call in tool_use_buffer:
                    if tool_call["name"] == "search_web":
                        query = tool_call["input"].get("query", "")
                        if query:
                            logger.info(f"AI 调用搜索工具: {query}")
                            print(
                                f"\n🔍 [搜索] 正在搜索 '{query}'...",
                                end="",
                                flush=True,
                            )

                            # 导入并执行搜索
                            from mind.tools.search_tool import search_web

                            search_result = await search_web(query, max_results=3)

                            if search_result:
                                print(" ✅")
                                logger.info("搜索完成")

                                # 将搜索结果添加到消息历史
                                messages.append(
                                    {
                                        "role": "assistant",
                                        "content": [
                                            {
                                                "type": "tool_use",
                                                "id": tool_call["id"],
                                                "name": "search_web",
                                                "input": {"query": query},
                                            }
                                        ],
                                    }
                                )
                                messages.append(
                                    {
                                        "role": "user",
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id": tool_call["id"],
                                                "content": search_result,
                                            }
                                        ],
                                    }
                                )

                                # 基于工具结果继续生成
                                # 重新打印角色名，因为搜索输出打断了对话
                                print(f"\n[{self.name}]: ", end="", flush=True)
                                response_text = await self._continue_response(
                                    messages, interrupt
                                )
                            else:
                                print(" ⚠️ (无结果)")
                                logger.warning("搜索未返回结果")
                    else:
                        logger.warning(f"未知工具: {tool_call['name']}")

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

    async def _continue_response(
        self, messages: list[MessageParam], interrupt: asyncio.Event
    ) -> str:
        """基于工具结果继续生成响应

        Args:
            messages: 包含工具结果的对话历史
            interrupt: 中断事件

        Returns:
            继续生成的响应文本
        """
        response_text = ""

        try:
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
            ) as stream:
                async for event in stream:
                    if interrupt.is_set():
                        logger.debug(f"智能体 {self.name} 继续响应被中断")
                        return response_text

                    if event.type == "text":
                        # 实时清理角色名前缀（如果 AI 误添加了）
                        text = event.text
                        if text.startswith(f"[{self.name}]:"):
                            text = text[len(f"[{self.name}]:") :].lstrip()
                        elif text.startswith(f"{self.name}:"):
                            text = text[len(f"{self.name}:") :].lstrip()

                        response_text += text
                        print(text, end="", flush=True)
                    elif event.type == "content_block_stop":
                        pass

        except Exception as e:
            logger.exception(f"继续响应出错: {e}")
            return response_text

        return response_text

    def add_document(self, doc: dict) -> None:
        """添加文档到搜索结果池

        Args:
            doc: Citations API 格式的文档字典
        """
        # 超过最大数量时，移除最旧的文档
        if len(self.search_documents) >= self.max_documents:
            self.search_documents.pop(0)

        self.search_documents.append(doc)

    def _format_messages_with_documents(
        self, messages: list[MessageParam]
    ) -> list[MessageParam]:
        """将文档池中的文档合并到消息中

        Args:
            messages: 原始消息列表

        Returns:
            合并了文档的消息列表
        """
        # 如果文档池为空，直接返回原消息
        if not self.search_documents:
            return messages

        # 只处理第一条用户消息（假设这是当前问题）
        formatted_messages: list[MessageParam] = []
        for msg in messages:
            if msg["role"] == "user":
                # 获取消息内容
                content = msg.get("content", "")

                # 构建新的内容：文档 + 原内容
                if isinstance(content, str):
                    # 字符串转为结构化格式
                    new_content = [
                        *self.search_documents,
                        {"type": "text", "text": content},
                    ]
                elif isinstance(content, list):
                    # 已经是结构化格式，在前面插入文档
                    new_content = list(self.search_documents) + list(content)
                else:
                    new_content = list(self.search_documents)

                formatted_messages.append(
                    MessageParam(role="user", content=new_content)
                )
            else:
                formatted_messages.append(msg)

        return formatted_messages

    def _cleanup_old_documents(self) -> None:
        """清理过期的文档

        根据 TTL（存活时间）移除超过保留轮次的文档。
        文档需要包含 age 字段来跟踪其存在轮次。
        """
        if self.document_ttl == 0:
            # TTL 为 0 表示不清理
            return

        # 过滤掉超过 TTL 的文档
        self.search_documents = [
            doc
            for doc in self.search_documents
            if doc.get("age", 0) < self.document_ttl
        ]

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
