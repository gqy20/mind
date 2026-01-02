"""Agent 类 - 对外接口

对话智能体的主入口，协调各个组件。
"""

import asyncio

from anthropic.types import MessageParam


class Agent:
    """对话智能体"""

    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: str | None = None,
    ):
        """初始化智能体

        Args:
            name: 智能体名称
            system_prompt: 系统提示词
            model: 使用的模型
        """
        self.name = name
        self.system_prompt = system_prompt
        self.model = model or "claude-sonnet-4-5-20250929"

    async def respond(
        self, messages: list[MessageParam], interrupt: "asyncio.Event"
    ) -> str | None:
        """生成响应（待实现）"""
        return "TODO"
