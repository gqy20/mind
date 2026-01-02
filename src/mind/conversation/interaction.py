"""用户交互处理模块

提供用户输入检测、输入模式和处理用户输入功能。
"""

import asyncio
import select
import sys

from anthropic.types import MessageParam
from rich.console import Console

from mind.logger import get_logger
from mind.memory import MemoryManager

logger = get_logger("mind.conversation.interaction")

console = Console()


class InteractionHandler:
    """用户交互处理器类

    负责检测用户输入、处理输入模式和用户命令。

    Attributes:
        manager: ConversationManager 实例的引用
    """

    def __init__(self, manager):
        """初始化交互处理器

        Args:
            manager: ConversationManager 实例，用于访问对话状态
        """
        self.manager = manager

    @staticmethod
    def is_input_ready() -> bool:
        """检查是否有输入可读（非阻塞）

        只在交互终端（TTY）中工作，非 TTY 环境返回 False

        Returns:
            是否有输入可读
        """
        # 检查是否在交互终端中运行
        if not sys.stdin.isatty():
            return False
        return bool(select.select([sys.stdin], [], [], 0)[0])

    async def input_mode(self):
        """输入模式 - 等待用户输入"""
        # 设置中断标志，停止 AI 输出
        self.manager.interrupt.set()
        logger.debug("进入用户输入模式")
        console.print("\n" + "=" * 50)
        console.print("📝 输入模式 (直接回车取消)")
        console.print("=" * 50)

        # 获取用户输入
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, ">>> "
            )
        except EOFError:
            user_input = ""

        # 清除中断标志
        self.manager.interrupt.clear()

        # 处理输入
        if user_input.strip():
            await self.handle_user_input(user_input)
        else:
            logger.debug("用户取消输入")
            console.print("❌ 取消输入，继续对话...\n")

    async def wait_for_user_input(self):
        """后台等待用户输入，设置中断标志

        这个方法在后台运行，定期检查 stdin 是否有输入可读。
        如果检测到输入，立即设置 interrupt 标志以中断正在进行的响应。
        """
        try:
            while True:
                if self.is_input_ready():
                    # 检测到输入，设置中断标志
                    self.manager.interrupt.set()
                    logger.debug("后台监听检测到用户输入，已设置中断标志")
                    break
                # 每 50ms 检查一次
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            # 任务被取消是正常的（当响应完成时）
            logger.debug("输入监听任务被取消")
            raise

    async def handle_user_input(self, user_input: str):
        """处理用户输入

        Args:
            user_input: 用户输入的文本
        """
        console.print(f"\n{'=' * 50}")
        console.print(f"👤 [用户]: {user_input}")
        console.print(f"{'=' * 50}\n")

        # 分析用户意图
        if user_input.strip().lower() in ["/quit", "/exit", "退出"]:
            self.manager.is_running = False
            logger.info("用户请求退出对话")
            console.print("对话结束")
        elif user_input.strip().lower() == "/clear":
            # 清空对话，保留主题
            self.manager.messages = self.manager.messages[:1]
            # 重置记忆管理器
            self.manager.memory = MemoryManager()
            topic_msg = self.manager.messages[0]
            self.manager.memory.add_message(
                topic_msg["role"], str(topic_msg["content"])
            )
            self.manager.turn = 0
            logger.info("用户重置对话历史")
            console.print("✅ 对话已重置\n")
        else:
            # 其他输入作为正常对话继续
            msg = MessageParam(role="user", content=user_input)
            self.manager.messages.append(msg)
            # 使用记忆管理器记录消息
            self.manager.memory.add_message(msg["role"], str(msg["content"]))
            logger.info(f"用户输入消息: {user_input[:50]}...")
            console.print("✅ 已发送，继续对话...\n")
