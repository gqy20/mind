"""
对话管理模块 - 协调两个智能体的对话

交互方式:
- AI 自动进行对话
- 用户按 Enter 打断当前对话
- 显示输入提示，用户输入消息
- 发送后 AI 继续自动对话
"""

import asyncio
import select
import sys
from dataclasses import dataclass, field

from anthropic.types.beta import BetaMessageParam

from mind.agent import Agent


def _is_input_ready():
    """检查是否有输入可读（非阻塞）"""
    return select.select([sys.stdin], [], [], 0)[0]


@dataclass
class ConversationManager:
    """对话管理器 - 协调两个智能体的对话循环"""

    agent_a: Agent
    agent_b: Agent
    messages: list[BetaMessageParam] = field(default_factory=list)
    interrupt: asyncio.Event = field(default_factory=asyncio.Event)
    user_wants_to_input: bool = False
    turn: int = 0
    current: int = 0  # 0=A, 1=B
    turn_interval: float = 0.3
    is_running: bool = True

    async def start(self, topic: str):
        """开始对话

        Args:
            topic: 对话主题
        """
        # 初始化主题
        self.messages.append(
            {
                "role": "user",
                "content": f"对话主题：{topic}\n\n请根据你们的角色展开探讨。",
            }
        )

        print("\n💡 提示: 按 Enter 打断对话并输入消息，Ctrl+C 退出\n")

        # 主对话循环
        try:
            while self.is_running:
                # 检查用户是否想输入
                if _is_input_ready():
                    # 读取并丢弃第一行（触发用的 Enter）
                    sys.stdin.readline()
                    # 进入输入模式
                    await self._input_mode()
                    continue

                # 执行一轮对话
                await self._turn()
                await asyncio.sleep(self.turn_interval)
        except KeyboardInterrupt:
            print("\n\n👋 对话已结束")

    async def _input_mode(self):
        """输入模式 - 等待用户输入"""
        # 设置中断标志，停止 AI 输出
        self.interrupt.set()
        print("\n" + "=" * 50)
        print("📝 输入模式 (直接回车取消)")
        print("=" * 50)

        # 获取用户输入
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, ">>> "
            )
        except EOFError:
            user_input = ""

        # 清除中断标志
        self.interrupt.clear()

        # 处理输入
        if user_input.strip():
            await self._handle_user_input(user_input)
        else:
            print("❌ 取消输入，继续对话...\n")

    async def _turn(self):
        """执行一轮对话"""
        # 确定当前发言的智能体
        current_agent = self.agent_a if self.current == 0 else self.agent_b

        # 打印智能体名称
        print(f"\n[{current_agent.name}]: ", end="", flush=True)

        # 智能体响应
        response = await current_agent.respond(self.messages, self.interrupt)

        print()  # 换行

        # 如果未被中断，记录响应
        if response is not None:
            self.messages.append({"role": "assistant", "content": response})
            self.turn += 1

        # 切换到下一个智能体
        self.current = 1 - self.current

    async def _handle_user_input(self, user_input: str):
        """处理用户输入"""
        print(f"\n{'=' * 50}")
        print(f"👤 [用户]: {user_input}")
        print(f"{'=' * 50}\n")

        # 分析用户意图
        if user_input.strip().lower() in ["/quit", "/exit", "退出"]:
            self.is_running = False
            print("对话结束")
        elif user_input.strip().lower() == "/clear":
            # 清空对话，保留主题
            self.messages = self.messages[:1]
            self.turn = 0
            print("✅ 对话已重置\n")
        else:
            # 其他输入作为正常对话继续
            self.messages.append({"role": "user", "content": user_input})
            print("✅ 已发送，继续对话...\n")
