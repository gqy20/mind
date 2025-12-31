"""
对话管理模块 - 协调两个智能体的对话

交互方式:
- AI 自动进行对话
- 用户按 Enter 打断当前对话
- 显示输入提示，用户输入消息
- 发送后 AI 继续自动对话
"""

import asyncio
import json
import re
import select
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast

from anthropic.types import MessageParam
from rich.console import Console

from mind.agent import Agent
from mind.logger import get_logger
from mind.memory import MemoryManager

logger = get_logger("mind.conversation")

# 对话记忆保存目录
MEMORY_DIR = Path("conversations")

# Rich console 用于进度条显示
console = Console()


def _is_input_ready():
    """检查是否有输入可读（非阻塞）"""
    return select.select([sys.stdin], [], [], 0)[0]


@dataclass
class ConversationManager:
    """对话管理器 - 协调两个智能体的对话循环"""

    agent_a: Agent
    agent_b: Agent
    messages: list[MessageParam] = field(default_factory=list)
    interrupt: asyncio.Event = field(default_factory=asyncio.Event)
    user_wants_to_input: bool = False
    turn: int = 0
    current: int = 0  # 0=A, 1=B
    turn_interval: float = 0.3
    is_running: bool = True
    # 记忆管理器
    memory: MemoryManager = field(default_factory=lambda: MemoryManager())
    # 对话主题（使用空字符串作为默认值）
    topic: str = ""
    # 对话开始时间（使用 None 作为默认值，在 start 时设置）
    start_time: datetime | None = None
    # 清理计数器
    _trim_count: int = 0
    # 对话总结
    summary: str = ""

    def save_conversation(self) -> Path:
        """保存对话到 JSON 文件

        Returns:
            保存的文件路径
        """
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        # 确保 start_time 已设置（对话结束时应该已经设置）
        if self.start_time is None:
            self.start_time = datetime.now()

        # 生成文件名：主题_时间戳.json
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        # 清理主题中的非法字符
        safe_topic = re.sub(r'[\\/*?:"<>|]', "_", self.topic)[:30]
        filename = f"{safe_topic}_{timestamp}.json"
        filepath = MEMORY_DIR / filename

        # 构建保存数据
        data = {
            "topic": self.topic,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "turn_count": self.turn,
            "agent_a": self.agent_a.name,
            "agent_b": self.agent_b.name,
            "trim_count": self._trim_count,
            "summary": self.summary,
            "messages": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in self.messages
            ],
        }

        # 保存到文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"对话已保存到: {filepath}")
        return filepath

    def should_exit_after_trim(self) -> bool:
        """判断是否应该在清理后退出

        Returns:
            是否应该退出
        """
        return self._trim_count >= self.memory.config.max_trim_count

    async def _summarize_conversation(self) -> str:
        """生成对话总结

        使用当前智能体对整体对话进行总结。

        Returns:
            对话总结文本
        """
        # 构建总结提示词
        content_preview = chr(
            10
        ).join(
            f"- {msg['role']}: {(msg['content'][:100] if isinstance(msg['content'], str) else str(cast(str, msg['content']))[:100])}..."  # noqa: E501
            for msg in self.messages[-20:]
        )
        summary_prompt = f"""请对以下对话进行总结，包括：

主题：{self.topic}

对话内容：
{content_preview}

请提供：
1. 核心观点总结（支持者的主要论点）
2. 反对观点总结（挑战者的主要论点）
3. 关键共识点
4. 主要分歧点

请用简洁的语言总结，不超过 300 字。"""

        # 使用 agent_a 生成总结
        messages_for_summary: list[MessageParam] = [
            cast(MessageParam, {"role": "user", "content": summary_prompt})
        ]

        try:
            response = await self.agent_a.respond(messages_for_summary, asyncio.Event())
            summary = response or "对话总结生成失败"
            logger.info(f"对话总结已生成: {len(summary)} 字")
            return summary
        except Exception as e:
            logger.error(f"生成对话总结失败: {e}")
            return "对话总结生成失败"

    def _show_token_progress(self):
        """显示 token 使用进度条"""
        tokens = self.memory._total_tokens
        max_tokens = self.memory.config.max_context
        percentage = min(tokens / max_tokens, 1.0)

        # 根据使用率选择颜色
        if percentage < 0.8:
            color = "[green]"
        elif percentage < 0.95:
            color = "[yellow]"
        else:
            color = "[red]"

        # 计算进度条宽度
        bar_width = 30
        filled = int(bar_width * percentage)
        bar = "█" * filled + "░" * (bar_width - filled)

        # 打印进度条（使用 \r 覆盖当前行）
        progress_text = (
            f"\r{color}Token:[{bar}] {tokens}/{max_tokens} ({percentage:.1%})[/{color}]"
        )
        console.print(progress_text, end="")

    async def start(self, topic: str):
        """开始对话

        Args:
            topic: 对话主题
        """
        # 保存主题和开始时间
        self.topic = topic
        self.start_time = datetime.now()

        # 初始化主题
        topic_msg = cast(
            MessageParam,
            {
                "role": "user",
                "content": f"对话主题：{topic}\n\n请根据你们的角色展开探讨。",
            },
        )
        self.messages.append(topic_msg)
        # 使用记忆管理器记录主题消息
        self.memory.add_message(topic_msg["role"], cast(str, topic_msg["content"]))
        logger.info(f"对话开始，主题: {topic}")

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
            logger.info("对话被用户中断")
            print("\n\n👋 对话已结束")
        finally:
            # 保存对话到文件
            filepath = self.save_conversation()
            print(f"📁 对话已保存到: {filepath}")

    async def _input_mode(self):
        """输入模式 - 等待用户输入"""
        # 设置中断标志，停止 AI 输出
        self.interrupt.set()
        logger.debug("进入用户输入模式")
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
            logger.debug("用户取消输入")
            print("❌ 取消输入，继续对话...\n")

    async def _turn(self):
        """执行一轮对话"""
        # 确定当前发言的智能体
        current_agent = self.agent_a if self.current == 0 else self.agent_b

        # 打印智能体名称（换行以避免覆盖进度条）
        print(f"\n[{current_agent.name}]: ", end="", flush=True)

        # 智能体响应
        response = await current_agent.respond(self.messages, self.interrupt)

        print()  # 换行

        # 如果未被中断，记录响应
        if response is not None:
            # 添加角色名前缀，使 AI 能区分不同智能体
            # 防御性去重：移除各种可能的前缀格式
            # 匹配: [角色名]:, [角色名]：, **角色名：**, 角色名：, 等
            patterns_to_remove = [
                rf"^\[{re.escape(current_agent.name)}\]:\s*",
                rf"^\[{re.escape(current_agent.name)}]\uFF1A\s*",  # 中文冒号
                rf"^\*\*{re.escape(current_agent.name)}\uFF1A\*\*\s*",  # 加粗+中文冒号
                rf"^\*\*{re.escape(current_agent.name)}:\*\*\s*",  # 加粗+英文冒号
                rf"^{re.escape(current_agent.name)}\uFF1A\s*",  # 纯角色名+中文冒号
                rf"^\[{re.escape(current_agent.name)}\]\s*\*\*{re.escape(current_agent.name)}\uFF1A\*\*\s*",  # noqa: E501
            ]
            for pattern in patterns_to_remove:
                response = re.sub(pattern, "", response, count=1).lstrip()

            formatted_content = f"[{current_agent.name}]: {response}"
            msg = cast(
                MessageParam,
                {"role": "assistant", "content": formatted_content},
            )
            self.messages.append(msg)
            # 使用记忆管理器记录消息
            self.memory.add_message(msg["role"], cast(str, msg["content"]))
            self.turn += 1
            logger.debug(f"轮次 {self.turn}: {current_agent.name} 响应完成")

            # 每3轮记录一次 token 使用情况
            if self.turn % 3 == 0:
                logger.info(  # noqa: E501
                    f"Token 使用: {self.memory._total_tokens}/{self.memory.config.max_context} "  # noqa: E501
                    f"({self.memory._total_tokens / self.memory.config.max_context:.1%})"  # noqa: E501
                )

            # 显示 token 进度条（前后各空一行）
            print()  # 对话内容和进度条之间的空行
            self._show_token_progress()
            print()  # 进度条后的空行

            # 检查记忆状态并在必要时清理
            status = self.memory.get_status()
            if status == "red":
                self._trim_count += 1
                logger.warning(  # noqa: E501
                    f"Token 超限 (第 {self._trim_count} 次)，开始清理对话历史..."
                )
                old_count = len(self.messages)
                self.messages = cast(
                    list[MessageParam],
                    self.memory.trim_messages(cast(list[dict], self.messages)),
                )
                new_count = len(self.messages)
                log_msg = (
                    f"清理完成: {old_count} → {new_count} 条消息, "
                    f"{self.memory._total_tokens} tokens"
                )
                logger.info(log_msg)

                # 检查是否需要自动退出
                if self.should_exit_after_trim():
                    print(f"\n{'=' * 60}")
                    warning_msg = (
                        f"⚠️  已达到最大清理次数 "
                        f"({self.memory.config.max_trim_count} 次)"
                    )
                    print(warning_msg)
                    print("正在生成对话总结...")
                    print(f"{'=' * 60}\n")

                    # 生成总结
                    self.summary = await self._summarize_conversation()

                    print(f"\n{'=' * 60}")
                    print("📝 对话总结")
                    print(f"{'=' * 60}")
                    print(f"{self.summary}\n")
                    print(f"{'=' * 60}")
                    print("💾 对话已保存（包含总结）")
                    print(f"{'=' * 60}\n")

                    # 标记退出
                    self.is_running = False
                    logger.info("达到最大清理次数，对话自动结束")
        else:
            logger.debug(f"轮次 {self.turn}: {current_agent.name} 响应被中断")

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
            logger.info("用户请求退出对话")
            print("对话结束")
        elif user_input.strip().lower() == "/clear":
            # 清空对话，保留主题
            self.messages = self.messages[:1]
            # 重置记忆管理器
            self.memory = MemoryManager()
            topic_msg = self.messages[0]
            self.memory.add_message(topic_msg["role"], cast(str, topic_msg["content"]))
            self.turn = 0
            logger.info("用户重置对话历史")
            print("✅ 对话已重置\n")
        else:
            # 其他输入作为正常对话继续
            msg = cast(MessageParam, {"role": "user", "content": user_input})
            self.messages.append(msg)
            # 使用记忆管理器记录消息
            self.memory.add_message(msg["role"], cast(str, msg["content"]))
            logger.info(f"用户输入消息: {user_input[:50]}...")
            print("✅ 已发送，继续对话...\n")
