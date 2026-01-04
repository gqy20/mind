"""响应处理逻辑

处理流式响应、文本累积、工具调用等。
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from anthropic import APIStatusError
from anthropic.types import ToolParam

from mind.agents.client import AnthropicClient
from mind.agents.utils import console, logger
from mind.config import SearchConfig
from mind.display.citations import display_citations, format_citations


@dataclass
class ResponseResult:
    """响应结果

    Attributes:
        text: 响应文本
        citations: 引用信息列表（原始数据）
        citations_lines: 格式化的引用文本行
    """

    text: str
    citations: list[dict]
    citations_lines: list[str]


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
        documents=None,
        stop_tokens: list[str] | None = None,
        mcp_tools: list[dict] | None = None,
        mcp_manager=None,
    ):
        """初始化响应处理器

        Args:
            client: Anthropic API 客户端
            search_history: 可选的搜索历史记录
            search_config: 搜索配置
            name: 智能体名称（用于日志）
            documents: 可选的文档池，用于存储搜索结果
            stop_tokens: 停止序列列表
            mcp_tools: 可选的 MCP 工具列表
            mcp_manager: 可选的 MCP 客户端管理器
        """
        self.client = client
        self.search_history = search_history
        self.search_config = search_config or SearchConfig()
        self.name = name
        self.documents = documents
        self.stop_tokens = stop_tokens
        self.mcp_tools = mcp_tools or []
        self.mcp_manager = mcp_manager

    def _handle_content_block_delta(
        self, event, response_text: str, has_text_delta: bool
    ) -> tuple[str, bool, list[dict]]:
        """处理 content_block_delta 事件

        Args:
            event: 流事件
            response_text: 当前累积的响应文本
            has_text_delta: 是否已处理过 text_delta

        Returns:
            (更新后的响应文本, 更新后的 has_text_delta, 新增的引用列表)
        """
        citations_buffer: list[dict] = []

        if event.type != "content_block_delta":
            return response_text, has_text_delta, citations_buffer

        if not (hasattr(event, "delta") and hasattr(event.delta, "type")):
            return response_text, has_text_delta, citations_buffer

        delta_type = event.delta.type

        if delta_type == "text_delta":
            text = getattr(event.delta, "text", "")
            response_text += text
            print(text, end="", flush=True)
            return response_text, True, citations_buffer

        elif delta_type == "citations_delta":
            # Citations API 官方规范：event.delta.citation（单数）
            # 参考：https://platform.claude.com/docs/en/api/messages
            if hasattr(event.delta, "citation"):
                citation = event.delta.citation
                citations_buffer.append(
                    {
                        "type": getattr(citation, "type", "unknown"),
                        "document_title": getattr(
                            citation, "document_title", "未知来源"
                        ),
                        "cited_text": getattr(citation, "cited_text", ""),
                        "document_index": getattr(citation, "document_index", 0),
                    }
                )
            return response_text, has_text_delta, citations_buffer

        return response_text, has_text_delta, citations_buffer

    def _handle_text_event(
        self, event, response_text: str, has_text_delta: bool
    ) -> tuple[str, bool]:
        """处理旧格式 text 事件

        Args:
            event: 流事件
            response_text: 当前累积的响应文本
            has_text_delta: 是否已处理过 text_delta

        Returns:
            (更新后的响应文本, 更新后的 has_text_delta)
        """
        if event.type != "text" or has_text_delta:
            return response_text, has_text_delta

        text = getattr(event, "text", "")
        response_text += text
        print(text, end="", flush=True)
        # 注意：旧格式 text 事件不改变 has_text_delta 标志
        # 这允许多个 text 事件被处理（与原始行为一致）
        return response_text, has_text_delta

    def _extract_tool_calls(self, event) -> list[dict]:
        """从 content_block_stop 事件中提取工具调用

        Args:
            event: 流事件

        Returns:
            工具调用列表，如果没有则返回空列表
        """
        if event.type != "content_block_stop":
            return []

        if not (
            hasattr(event, "content_block") and hasattr(event.content_block, "type")
        ):
            return []

        if event.content_block.type != "tool_use":
            return []

        return [
            {
                "type": "tool_use",
                "id": getattr(event.content_block, "id", ""),
                "name": getattr(event.content_block, "name", ""),
                "input": getattr(event.content_block, "input", {}),
            }
        ]

    def _append_tool_messages(
        self, messages: list, tool_call: dict, query: str, result_text: str
    ) -> None:
        """添加工具调用和结果消息到对话历史

        Args:
            messages: 消息列表（会被原地修改）
            tool_call: 工具调用信息字典
            query: 搜索查询
            result_text: 搜索结果文本
        """
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
                        "content": result_text,
                    }
                ],
            }
        )

    async def respond(
        self,
        messages: list["MessageParam"],
        system: str,
        interrupt: asyncio.Event,
    ) -> ResponseResult | None:
        """生成响应

        Args:
            messages: 对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            ResponseResult 包含响应文本和引用信息，如果被中断则返回 None
        """
        if interrupt.is_set():
            logger.debug(f"智能体 {self.name} 响应被中断")
            return None

        response_text = ""
        tool_use_buffer: list[dict] | None = None
        citations_buffer: list[dict] = []
        has_text_delta = False  # 标记是否处理过 text_delta

        logger.debug(f"智能体 {self.name} 开始响应，历史消息数: {len(messages)}")

        # 获取 documents 列表（用于 Citations API）
        docs_list = self.documents.documents if self.documents else None

        try:
            # 第一轮：生成响应（可能包含工具调用）
            async for event in self.client.stream(
                messages=messages,
                system=system,
                tools=_get_tools_schema(self.mcp_tools),
                documents=docs_list,
                stop_tokens=self.stop_tokens,
            ):
                if interrupt.is_set():
                    logger.debug(f"智能体 {self.name} 响应中途被中断")
                    return None

                # 处理 content_block_delta 事件（新格式）
                if event.type == "content_block_delta":
                    response_text, has_text_delta, new_citations = (
                        self._handle_content_block_delta(
                            event, response_text, has_text_delta
                        )
                    )
                    citations_buffer.extend(new_citations)

                # 处理 text 事件（旧格式）
                elif event.type == "text":
                    response_text, has_text_delta = self._handle_text_event(
                        event, response_text, has_text_delta
                    )

                # 处理工具调用
                elif event.type == "content_block_stop":
                    tool_calls = self._extract_tool_calls(event)
                    if tool_calls:
                        logger.debug(f"检测到工具调用完成: {tool_calls[0]['name']}")
                        if tool_use_buffer is None:
                            tool_use_buffer = []
                        tool_use_buffer.extend(tool_calls)

            # 处理工具调用
            buffer_status = (
                f"{len(tool_use_buffer)} 个工具调用"
                if tool_use_buffer
                else "0 个工具调用"
            )
            logger.debug(f"工具调用检测完成，buffer 状态: {buffer_status}")

            if tool_use_buffer:
                # 串行执行所有工具调用，传递 system 参数
                serial_result = await self._execute_tools_serial(
                    tool_use_buffer, messages, system, interrupt
                )
                if serial_result is not None:
                    response_text = serial_result

        except APIStatusError as e:
            self._handle_api_status_error(e)
            return None

        except TimeoutError:
            self._handle_timeout_error()
            return None

        except OSError as e:
            self._handle_os_error(e)
            return None

        except Exception as e:
            logger.exception(f"未知错误: {self.name}, 错误: {e}")
            console.print(f"\n[red]❌ 未知错误：{e}[/red]")
            return None

        # 格式化引用列表（如果有）
        citations_lines: list[str] = []
        if citations_buffer:
            # 仍然在交互模式下显示引用
            display_citations(citations_buffer)
            # 同时生成格式化的文本行（用于非交互模式）
            citations_lines = format_citations(citations_buffer)

        logger.debug(f"智能体 {self.name} 响应完成，长度: {len(response_text)}")
        return ResponseResult(
            text=response_text,
            citations=citations_buffer,
            citations_lines=citations_lines,
        )

    async def _continue_response(
        self, messages: list["MessageParam"], system: str, interrupt: asyncio.Event
    ) -> str:
        """基于工具结果继续生成响应

        继续生成时禁止工具调用，强制 AI 基于已有工具结果生成文本。

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

        # 获取 documents 列表（用于 Citations API）
        docs_list = self.documents.documents if self.documents else None

        try:
            # 继续生成时禁止工具调用，强制 AI 生成文本
            # 使用 omit_tools=True 完全省略 tools 参数
            async for event in self.client.stream(
                messages=messages,
                system=system,
                tools=None,  # 不传入工具，强制 AI 生成文本
                documents=docs_list,
                stop_tokens=self.stop_tokens,
                omit_tools=True,  # 通过 omit_tools 参数明确禁止工具
            ):
                if interrupt.is_set():
                    logger.debug(f"智能体 {self.name} 继续响应被中断")
                    return response_text

                # 处理 content_block_delta 事件（新格式）
                if event.type == "content_block_delta":
                    response_text, has_text_delta, new_citations = (
                        self._handle_content_block_delta(
                            event, response_text, has_text_delta
                        )
                    )
                    citations_buffer.extend(new_citations)

                # 处理 text 事件（旧格式）
                elif event.type == "text":
                    response_text, has_text_delta = self._handle_text_event(
                        event, response_text, has_text_delta
                    )

        except Exception as e:
            logger.exception(f"继续响应出错: {e}")
            return response_text

        # 显示引用列表（如果有）
        if citations_buffer:
            display_citations(citations_buffer)

        return response_text

    async def _retry_without_tools(
        self, messages: list["MessageParam"], system: str, interrupt: asyncio.Event
    ) -> str:
        """重试响应时不允许工具调用

        当 AI 在继续生成时只调用工具而不输出内容，调用此方法重试一次。
        重试时不传入 tools 参数，强制 AI 输出内容。

        Args:
            messages: 对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            重试后的响应文本
        """
        # 检查是否已经重试过
        if not hasattr(self, "_empty_retry_count"):
            self._empty_retry_count = 0

        # 最多重试 1 次
        if self._empty_retry_count >= 1:
            logger.warning("已达到最大重试次数（1 次），返回空响应")
            self._empty_retry_count = 0  # 重置计数器
            return ""

        self._empty_retry_count += 1
        logger.info("检测到空响应，进行第 1 次重试（禁止工具调用）...")

        # 增强系统提示词，明确要求 AI 输出内容
        enhanced_system = (
            system
            + "\n\n注意：搜索已完成，请直接基于已有结果输出回答内容，不要调用任何工具。"
        )

        response_text = ""
        has_text_delta = False
        citations_buffer: list[dict] = []

        # 获取 documents 列表（用于 Citations API）
        docs_list = self.documents.documents if self.documents else None

        try:
            # 关键：使用 omit_tools=True 禁止工具调用
            async for event in self.client.stream(
                messages=messages,
                system=enhanced_system,
                tools=None,
                omit_tools=True,  # 完全省略 tools 参数
                documents=docs_list,
                stop_tokens=self.stop_tokens,
            ):
                if interrupt.is_set():
                    logger.debug(f"智能体 {self.name} 重试响应被中断")
                    return response_text

                # 处理 content_block_delta 事件（新格式）
                if event.type == "content_block_delta":
                    response_text, has_text_delta, new_citations = (
                        self._handle_content_block_delta(
                            event, response_text, has_text_delta
                        )
                    )
                    citations_buffer.extend(new_citations)

                # 处理 text 事件（旧格式）
                elif event.type == "text":
                    response_text, has_text_delta = self._handle_text_event(
                        event, response_text, has_text_delta
                    )

        except Exception as e:
            logger.exception(f"重试响应出错: {e}")
            return response_text
        finally:
            # 重置计数器，为下次响应做准备
            self._empty_retry_count = 0

        # 显示引用列表（如果有）
        if citations_buffer:
            display_citations(citations_buffer)

        logger.info(f"重试完成，生成响应长度: {len(response_text)}")
        return response_text

    async def _execute_tools_serial(
        self,
        tool_calls: list[dict],
        messages: list["MessageParam"],
        system: str,
        interrupt: asyncio.Event,
    ) -> str | None:
        """串行执行多个工具调用

        与并行执行的区别：
        - 并行：所有工具同时执行，然后一次性收集结果
        - 串行：工具按顺序执行，一个完成后才执行下一个

        Args:
            tool_calls: 工具调用列表
            messages: 对话历史
            system: 系统提示词
            interrupt: 中断事件

        Returns:
            继续生成的响应文本
        """
        if not tool_calls:
            return None

        logger.info(f"开始串行执行 {len(tool_calls)} 个工具调用")

        # 收集 tool_use 和 tool_result 块
        tool_use_blocks: list[dict] = []
        tool_result_blocks: list[dict] = []

        # 执行单个工具的内部函数
        async def execute_single_tool(tool_call: dict) -> dict | None:
            """执行单个工具并返回结果

            Returns:
                (tool_call_id, result_text) 或 None
            """
            tool_name = tool_call.get("name", "")

            # 处理内置搜索工具
            if tool_name == "search_web":
                result = await self._execute_tool_search(
                    tool_call, messages, system, interrupt
                )
                return {"id": tool_call.get("id"), "result": result}

            # 处理 MCP 工具
            if self.mcp_manager:
                # 检查是否是 MCP 工具
                mcp_tool_names = [tool.get("name") for tool in self.mcp_tools]
                if tool_name in mcp_tool_names:
                    logger.info(f"调用 MCP 工具: {tool_name}")
                    print(f"\n🔧 [MCP] 正在调用 {tool_name}...", end="", flush=True)

                    # 获取工具参数
                    arguments = tool_call.get("input", {})

                    # 调用 MCP 工具
                    result = await self.mcp_manager.call_tool(tool_name, arguments)

                    if result:
                        print(" ✅")
                        logger.info(f"MCP 工具 {tool_name} 返回结果")
                        return {"id": tool_call.get("id"), "result": str(result)}
                    else:
                        print(" ⚠️ (失败)")
                        logger.warning(f"MCP 工具 {tool_name} 执行失败")
                        return {"id": tool_call.get("id"), "result": "工具执行失败"}

            # 未知工具
            logger.warning(f"未知工具: {tool_name}")
            return {"id": tool_call.get("id"), "result": "未知工具"}

        # 串行执行每个工具
        for i, tool_call in enumerate(tool_calls):
            logger.debug(f"执行第 {i + 1}/{len(tool_calls)} 个工具")

            # 1. 收集 tool_use 块
            tool_use_blocks.append(
                {
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call.get("name", ""),
                    "input": tool_call.get("input", {}),
                }
            )

            # 2. 执行工具
            try:
                result = await execute_single_tool(tool_call)
                if result:
                    # 3. 收集 tool_result 块
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": result["id"],
                            "content": result.get("result") or "",
                        }
                    )
                else:
                    # 工具执行失败，添加错误结果
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_call["id"],
                            "content": "工具执行失败",
                        }
                    )
            except Exception as e:
                logger.exception(f"工具执行异常: {tool_call.get('name')}")
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": f"错误: {e}",
                    }
                )

        if not tool_result_blocks:
            logger.warning("所有工具执行都失败了")
            return None

        # 一次性添加所有 tool_use 和 tool_result 到消息历史
        messages.append({"role": "assistant", "content": tool_use_blocks})  # type: ignore[typeddict-item]
        messages.append({"role": "user", "content": tool_result_blocks})  # type: ignore[typeddict-item]

        logger.debug(
            f"已添加 {len(tool_use_blocks)} 个 tool_use 和 "
            f"{len(tool_result_blocks)} 个 tool_result 到消息历史"
        )

        # 基于工具结果继续生成，传递 system 参数
        return await self._continue_response(messages, system, interrupt)

    async def _execute_tool_search(
        self,
        tool_call: dict,
        messages: list["MessageParam"],
        system: str,
        interrupt: asyncio.Event,
    ) -> str | None:
        """执行搜索工具调用

        Args:
            tool_call: 工具调用信息
            messages: 对话历史
            system: 系统提示词
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

                # 转换为 Citations 文档并添加到文档池
                from mind.agents.documents import DocumentPool

                citation_docs = DocumentPool.from_search_history(latest_searches)
                if self.documents:
                    for doc in citation_docs:
                        self.documents.add(doc)

                # 构建工具结果消息（包含完整的搜索结果内容）
                # 这样 AI 可以引用具体的内容
                result_lines = [f"**网络搜索结果**: {query}\n"]
                result_lines.append(
                    "请在回复时使用引用标记，例如：`根据研究[1]，...`\n"
                )

                for i, result in enumerate(raw_results, 1):
                    title = result.get("title", "无标题")
                    href = result.get("href", "")
                    body = result.get("body", "")

                    result_lines.append(f"[{i}] {title}")
                    if href:
                        result_lines.append(f"    来源: {href}")
                    if body:
                        # 限制摘要长度
                        short_body = body[:150] + "..." if len(body) > 150 else body
                        result_lines.append(f"    内容: {short_body}")
                    result_lines.append("")

                search_result_text = "\n".join(result_lines)
                self._append_tool_messages(
                    messages, tool_call, query, search_result_text
                )

                # 基于工具结果继续生成，传递 system 参数
                print(f"\n[{self.name}]: ", end="", flush=True)
                return await self._continue_response(messages, system, interrupt)

            # 回退到原始流程（无 SearchHistory）
            from mind.tools.search_tool import search_web

            search_result = await search_web(
                query,
                max_results=self.search_config.max_results,
            )

            # 将搜索结果添加到消息历史
            self._append_tool_messages(messages, tool_call, query, search_result or "")

            # 基于工具结果继续生成，传递 system 参数
            print(f"\n[{self.name}]: ", end="", flush=True)
            return await self._continue_response(messages, system, interrupt)
        else:
            print(" ⚠️ (无结果)")
            logger.warning("搜索未返回结果")
            return None

    def _handle_api_status_error(self, e: APIStatusError) -> None:
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

    def _handle_timeout_error(self) -> None:
        """处理超时错误

        Returns:
            None（表示错误处理完成）
        """
        logger.error(f"请求超时: {self.name}")
        console.print("\n[red]❌ 请求超时：网络连接超时，请检查网络设置[/red]")

    def _handle_os_error(self, e: OSError) -> None:
        """处理网络错误

        Args:
            e: 操作系统错误

        Returns:
            None（表示错误处理完成）
        """
        logger.error(f"网络错误: {self.name}, 错误: {e}")
        console.print(f"\n[red]❌ 网络错误：{e}[/red]")


def _get_tools_schema(mcp_tools: list[dict] | None = None) -> list[ToolParam]:
    """获取可用工具的 schema 定义

    Args:
        mcp_tools: 可选的 MCP 工具列表

    Returns:
        工具 schema 列表
    """
    # 内置工具
    tools = [
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

    # 添加 MCP 工具
    if mcp_tools:
        for tool in mcp_tools:
            tools.append(
                ToolParam(
                    name=tool.get("name", "unknown"),
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
            )

    return tools
