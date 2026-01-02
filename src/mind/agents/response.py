"""响应处理逻辑

处理流式响应、文本累积、工具调用等。
"""

import asyncio
from typing import TYPE_CHECKING

from anthropic import APIStatusError
from anthropic.types import ToolParam

from mind.agents.citations import display_citations
from mind.agents.client import AnthropicClient
from mind.agents.utils import console, logger
from mind.prompts import SearchConfig

if TYPE_CHECKING:
    from anthropic.types import MessageParam


class ResponseHandler:
    """响应处理器 - 处理流式响应和工具调用"""

    def __init__(
        self,
        client: AnthropicClient,
        search_history=None,
        search_config: SearchConfig | None = None,
        name: str = "Agent",
    ):
        """初始化响应处理器

        Args:
            client: Anthropic API 客户端
            search_history: 可选的搜索历史记录
            search_config: 搜索配置
            name: 智能体名称（用于日志）
        """
        self.client = client
        self.search_history = search_history
        self.search_config = search_config or SearchConfig()
        self.name = name

    async def respond(
        self,
        messages: list["MessageParam"],
        system: str,
        interrupt: asyncio.Event,
    ) -> str | None:
        """生成响应

        Args:
            messages: 对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            完整响应文本，如果被中断则返回 None
        """
        if interrupt.is_set():
            logger.debug(f"智能体 {self.name} 响应被中断")
            return None

        response_text = ""
        tool_use_buffer: list[dict] | None = None
        citations_buffer: list[dict] = []
        has_text_delta = False  # 标记是否处理过 text_delta

        logger.debug(f"智能体 {self.name} 开始响应，历史消息数: {len(messages)}")

        try:
            # 第一轮：生成响应（可能包含工具调用）
            async for event in self.client.stream(
                messages=messages,
                system=system,
                tools=_get_tools_schema(),
            ):
                if interrupt.is_set():
                    logger.debug(f"智能体 {self.name} 响应中途被中断")
                    return None

                # 处理 content_block_delta 事件（新格式）
                if event.type == "content_block_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "type"):
                        delta_type = event.delta.type

                        # 处理文本增量
                        if delta_type == "text_delta":
                            has_text_delta = True  # 标记已处理增量
                            text = getattr(event.delta, "text", "")
                            # 清理角色名前缀
                            from mind.agents.utils import _clean_agent_name_prefix

                            text = _clean_agent_name_prefix(text)

                            response_text += text
                            print(text, end="", flush=True)

                        # 处理引用增量
                        elif delta_type == "citations_delta":
                            # 捕获引用信息
                            if hasattr(event.delta, "citations"):
                                for citation in event.delta.citations:
                                    citations_buffer.append(
                                        {
                                            "type": getattr(
                                                citation, "type", "unknown"
                                            ),
                                            "document_title": getattr(
                                                citation,
                                                "document_title",
                                                "未知来源",
                                            ),
                                            "cited_text": getattr(
                                                citation, "cited_text", ""
                                            ),
                                        }
                                    )

                # 处理 text 事件（旧格式）
                # 只在没有处理过 text_delta 时才处理，避免重复
                elif event.type == "text" and not has_text_delta:
                    from mind.agents.utils import _clean_agent_name_prefix

                    text = getattr(event, "text", "")
                    text = _clean_agent_name_prefix(text)

                    response_text += text
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
                                    "name": getattr(event.content_block, "name", ""),
                                    "input": getattr(event.content_block, "input", {}),
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
                            result = await self._execute_tool_search(
                                tool_call, messages, interrupt
                            )
                            if result is not None:
                                response_text = result
                    else:
                        logger.warning(f"未知工具: {tool_call['name']}")

        except APIStatusError as e:
            return self._handle_api_status_error(e)

        except TimeoutError:
            return self._handle_timeout_error()

        except OSError as e:
            return self._handle_os_error(e)

        except Exception as e:
            logger.exception(f"未知错误: {self.name}, 错误: {e}")
            console.print(f"\n[red]❌ 未知错误：{e}[/red]")
            return None

        # 显示引用列表（如果有）
        if citations_buffer:
            display_citations(citations_buffer)

        logger.debug(f"智能体 {self.name} 响应完成，长度: {len(response_text)}")
        return response_text

    async def _continue_response(
        self, messages: list["MessageParam"], system: str, interrupt: asyncio.Event
    ) -> str:
        """基于工具结果继续生成响应

        Args:
            messages: 包含工具结果的对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            继续生成的响应文本
        """
        response_text = ""
        has_text_delta = False  # 标记是否处理过 text_delta
        citations_buffer: list[dict] = []  # 捕获引用信息

        try:
            async for event in self.client.stream(
                messages=messages,
                system=system,
            ):
                if interrupt.is_set():
                    logger.debug(f"智能体 {self.name} 继续响应被中断")
                    return response_text

                # 处理 content_block_delta 事件（新格式）
                if event.type == "content_block_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "type"):
                        delta_type = event.delta.type

                        # 处理文本增量
                        if delta_type == "text_delta":
                            has_text_delta = True  # 标记已处理增量
                            from mind.agents.utils import _clean_agent_name_prefix

                            text = getattr(event.delta, "text", "")
                            text = _clean_agent_name_prefix(text)

                            response_text += text
                            print(text, end="", flush=True)

                        # 处理引用增量
                        elif delta_type == "citations_delta":
                            # 捕获引用信息
                            if hasattr(event.delta, "citations"):
                                for citation in event.delta.citations:
                                    citations_buffer.append(
                                        {
                                            "type": getattr(
                                                citation, "type", "unknown"
                                            ),
                                            "document_title": getattr(
                                                citation,
                                                "document_title",
                                                "未知来源",
                                            ),
                                            "cited_text": getattr(
                                                citation, "cited_text", ""
                                            ),
                                        }
                                    )

                # 处理 text 事件（旧格式）
                # 只在没有处理过 text_delta 时才处理，避免重复
                elif event.type == "text" and not has_text_delta:
                    from mind.agents.utils import _clean_agent_name_prefix

                    text = getattr(event, "text", "")
                    text = _clean_agent_name_prefix(text)

                    response_text += text
                    print(text, end="", flush=True)

                elif event.type == "content_block_stop":
                    pass

        except Exception as e:
            logger.exception(f"继续响应出错: {e}")
            return response_text

        # 显示引用列表（如果有）
        if citations_buffer:
            display_citations(citations_buffer)

        return response_text

    async def _execute_tool_search(
        self,
        tool_call: dict,
        messages: list["MessageParam"],
        interrupt: asyncio.Event,
    ) -> str | None:
        """执行搜索工具调用

        Args:
            tool_call: 工具调用信息
            messages: 对话历史
            interrupt: 中断事件

        Returns:
            响应文本
        """
        query = tool_call["input"].get("query", "")
        if not query:
            return None

        logger.info(f"AI 调用搜索工具: {query}")
        print(f"\n🔍 [搜索] 正在搜索 '{query}'...", end="", flush=True)

        # 导入并执行搜索
        from mind.tools.search_tool import _search_sync

        # 执行搜索获取原始结果
        raw_results = await _search_sync(
            query, max_results=self.search_config.max_results
        )

        if raw_results:
            print(" ✅")
            logger.info("搜索完成")

            # 如果有 search_history，保存结果并转换为 Citations 文档
            if self.search_history:
                # 保存搜索结果到历史
                self.search_history.save_search(query, raw_results)

                # 获取最新的搜索记录（包括当前这次）
                latest_searches = self.search_history.get_latest(
                    limit=self.search_config.history_limit
                )

                # 转换为 Citations 文档
                from mind.agents.documents import DocumentPool

                DocumentPool.from_search_history(latest_searches)

                # 注意：这里需要与 Agent 集成来添加文档
                # 暂时返回 None，表示需要继续处理
                return None

            # 回退到原始流程（无 SearchHistory）
            from mind.tools.search_tool import search_web

            search_result = await search_web(
                query,
                max_results=self.search_config.max_results,
            )

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
                            "content": search_result or "",
                        }
                    ],
                }
            )

            # 基于工具结果继续生成
            print(f"\n[{self.name}]: ", end="", flush=True)
            return await self._continue_response(messages, "", interrupt)
        else:
            print(" ⚠️ (无结果)")
            logger.warning("搜索未返回结果")
            return None

    def _handle_api_status_error(self, e: APIStatusError) -> str | None:
        """处理 API 状态错误

        Args:
            e: API 状态错误

        Returns:
            None（表示错误处理完成）
        """
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

    def _handle_timeout_error(self) -> str | None:
        """处理超时错误

        Returns:
            None（表示错误处理完成）
        """
        logger.error(f"请求超时: {self.name}")
        console.print("\n[red]❌ 请求超时：网络连接超时，请检查网络设置[/red]")
        return None

    def _handle_os_error(self, e: OSError) -> str | None:
        """处理网络错误

        Args:
            e: 操作系统错误

        Returns:
            None（表示错误处理完成）
        """
        logger.error(f"网络错误: {self.name}, 错误: {e}")
        console.print(f"\n[red]❌ 网络错误：{e}[/red]")
        return None


def _get_tools_schema() -> list[ToolParam]:
    """获取可用工具的 schema 定义

    Returns:
        工具 schema 列表
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
