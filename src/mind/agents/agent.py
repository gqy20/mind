"""Agent 类 - 对外接口

对话智能体的主入口，协调各个组件。
"""

import asyncio
import os
from typing import TYPE_CHECKING, Any

from mind.agents.client import AnthropicClient
from mind.agents.conversation_analyzer import ConversationAnalyzer
from mind.agents.documents import DocumentPool
from mind.agents.prompt_builder import PromptBuilder
from mind.agents.response import ResponseHandler
from mind.config import SearchConfig, SettingsConfig
from mind.logger import get_logger

# 默认模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

if TYPE_CHECKING:
    from anthropic.types import MessageParam

# 日志器
logger = get_logger("mind.agents.agent")


class Agent:
    """对话智能体 - 对外统一接口"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
        tool_agent: Any = None,
        settings: SettingsConfig | None = None,
    ):
        """初始化智能体

        Args:
            name: 智能体名称
            system_prompt: 系统提示词
            model: 使用的模型，默认从环境变量 ANTHROPIC_MODEL 读取
            tool_agent: 可选的工具智能体（向后兼容）
            settings: 可选的设置配置（向后兼容）
        """
        if not name or not name.strip():
            raise ValueError("名称不能为空")

        self.name = name
        self.model = model or DEFAULT_MODEL
        self.tool_agent = tool_agent

        # 从配置中读取设置
        if settings:
            self.max_documents = settings.documents.max_documents
            self.document_ttl = settings.documents.ttl
            search_config = settings.search
        else:
            self.max_documents = 10
            self.document_ttl = 5
            search_config = SearchConfig()

        # 增强提示词（添加工具使用说明和时间感知）
        prompt_builder = PromptBuilder(system_prompt)
        has_tools = True  # 所有智能体都有搜索工具
        self.system_prompt = prompt_builder.build(
            has_tools=has_tools, tool_agent=tool_agent
        )

        # 初始化各个组件
        self.client = AnthropicClient(model=self.model)
        self.documents = DocumentPool(
            max_documents=self.max_documents, ttl=self.document_ttl
        )

        # search_history 由 ConversationManager 设置
        self.search_history = None

        # 响应处理器
        self.response_handler = ResponseHandler(
            client=self.client,
            search_history=self.search_history,
            search_config=search_config,
            name=self.name,
            documents=self.documents,
        )

        # 对话分析器
        self.analyzer = ConversationAnalyzer()

        logger.info(f"智能体初始化: {self.name}, 模型: {self.model}")

    async def respond(
        self, messages: list["MessageParam"], interrupt: asyncio.Event
    ) -> str | None:
        """生成响应

        委托给 ResponseHandler 处理。

        Args:
            messages: 对话历史
            interrupt: 中断事件

        Returns:
            完整响应文本，如果被中断则返回 None
        """
        # 如果需要，可以在消息中合并文档池
        formatted_messages = self._format_messages_with_documents(messages)

        result = await self.response_handler.respond(
            messages=formatted_messages,
            system=self.system_prompt,
            interrupt=interrupt,
        )

        # 为了向后兼容，返回 ResponseResult.text
        # 但将引用信息存储在实例属性中，供需要时访问
        self._last_citations_lines = result.citations_lines if result else []

        return result.text if result else None

    def add_document(self, doc: dict) -> None:
        """添加文档到文档池

        委托给 DocumentPool 处理。

        Args:
            doc: Citations API 格式的文档字典
        """
        self.documents.add(doc)

    async def query_tool(
        self, question: str, messages: list["MessageParam"] | None = None
    ) -> str | None:
        """分析对话上下文

        使用 ConversationAnalyzer 分析对话。

        Args:
            question: 查询问题（注意：当前版本忽略此参数，分析全部对话）
            messages: 对话历史记录

        Returns:
            对话摘要，如果对话为空或分析失败则返回 None
        """
        if not messages:
            logger.debug(f"智能体 {self.name} 对话历史为空")
            return None

        return self.analyzer.analyze(messages)

    def _format_messages_with_documents(
        self, messages: list["MessageParam"]
    ) -> list["MessageParam"]:
        """将文档池中的文档合并到消息中

        Args:
            messages: 原始消息列表

        Returns:
            合并了文档的消息列表
        """
        return self.documents.merge_into_messages(messages)

    @property
    def search_documents(self) -> list:
        """获取搜索文档列表（向后兼容）

        Returns:
            文档池中的文档列表
        """
        return self.documents.documents

    def set_search_history(self, search_history) -> None:
        """设置搜索历史记录

        Args:
            search_history: 搜索历史记录对象
        """
        self.search_history = search_history
        self.response_handler.search_history = search_history
