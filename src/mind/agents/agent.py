"""Agent 类 - 对外接口

对话智能体的主入口，协调各个组件。
"""

import asyncio
import os
from typing import TYPE_CHECKING, Any

from mind.agents.client import AnthropicClient
from mind.agents.documents import DocumentPool
from mind.agents.response import ResponseHandler

# 默认模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

if TYPE_CHECKING:
    from anthropic.types import MessageParam


class Agent:
    """对话智能体 - 对外统一接口"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
        tool_agent: Any = None,
        settings: Any = None,
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
        self.system_prompt = system_prompt
        self.model = model or DEFAULT_MODEL

        # 初始化各个组件
        self.client = AnthropicClient(model=self.model)
        self.documents = DocumentPool()
        self.response_handler = ResponseHandler(
            client=self.client,
            search_history=None,
        )

        # 向后兼容属性
        self.tool_agent = tool_agent
        self.search_history = None
        self.max_documents = 10
        self.document_ttl = 5

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
        return await self.response_handler.respond(
            messages=messages,
            system=self.system_prompt,
            interrupt=interrupt,
        )

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
        """分析对话上下文（待实现）

        Args:
            question: 查询问题
            messages: 对话历史记录

        Returns:
            对话摘要，如果对话为空或分析失败则返回 None
        """
        # TODO: 实现对话分析逻辑
        return None
