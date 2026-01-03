"""对话结束处理模块

处理 AI 的对话结束提议和用户确认流程。
"""

import asyncio

from anthropic.types import MessageParam
from rich.console import Console

from mind.conversation.ending_detector import EndProposal
from mind.logger import get_logger

logger = get_logger("mind.conversation.ending")

console = Console()


class EndingHandler:
    """对话结束处理器类

    负责处理 AI 提出的结束提议，获取用户确认，并执行相应操作。

    Attributes:
        manager: ConversationManager 实例的引用
    """

    def __init__(self, manager):
        """初始化结束处理器

        Args:
            manager: ConversationManager 实例，用于访问对话状态
        """
        self.manager = manager

    async def handle_proposal(self, agent_name: str, response: str) -> None:
        """处理 AI 的对话结束提议

        Args:
            agent_name: 请求结束的智能体名称
            response: 完整响应（包含结束标记）
        """
        # 清理响应用于显示和保存
        clean_response = self.manager.end_detector.clean_response(response)

        # 先将清理后的响应添加到消息历史（无论用户选择结束还是继续）
        formatted_content = f"[{agent_name}]: {clean_response}"
        msg = MessageParam(role="assistant", content=formatted_content)
        self.manager.messages.append(msg)
        self.manager.memory.add_message(msg["role"], str(msg["content"]))
        logger.info("已添加结束提议到消息历史（已清理 END 标记）")

        # 创建结束提议
        proposal = EndProposal(
            agent_name=agent_name,
            response_text=response,
            response_clean=clean_response,
        )

        # 显示结束提示
        console.print(f"\n{'=' * 60}")
        console.print(f"💡 {agent_name} 建议结束对话")
        console.print(f"{'=' * 60}")
        console.print(f"\n最后发言:\n{clean_response}\n")
        console.print(f"{'=' * 60}")
        console.print("\n按 Enter 确认结束，或输入其他内容继续对话...")
        print("> ", end="", flush=True)  # 使用标准 print 以支持 flush

        # 获取用户输入
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(None, input)
        except EOFError:
            user_input = ""

        console.print()  # 换行

        if not user_input.strip():
            # 用户确认结束
            proposal.confirm()
            logger.info("用户确认结束对话")

            # 生成对话总结
            console.print(f"\n{'=' * 60}")
            console.print("正在生成对话总结...")
            console.print(f"{'=' * 60}\n")
            self.manager.summary = await self.manager._summarize_conversation()

            console.print(f"\n{'=' * 60}")
            console.print("📝 对话总结")
            console.print(f"{'=' * 60}")
            console.print(f"{self.manager.summary}\n")
            console.print(f"{'=' * 60}")
            console.print("💾 对话已保存（包含总结）")
            console.print(f"{'=' * 60}\n")

            # 保存对话并退出
            self.manager.is_running = False
        else:
            # 用户想继续
            logger.info("用户选择继续对话")

            # 将用户输入添加到对话历史
            msg = MessageParam(role="user", content=user_input)
            self.manager.messages.append(msg)
            self.manager.memory.add_message(msg["role"], str(msg["content"]))

            console.print(f"\n{'=' * 60}")
            console.print("✅ 继续对话...")
            console.print(f"{'=' * 60}\n")
