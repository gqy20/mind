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
    # 是否启用工具（默认不启用）
    enable_tools: bool = False
    # 工具调用间隔（轮数），0 表示禁用自动调用
    tool_interval: int = 5
    # 是否启用网络搜索（默认不启用）
    enable_search: bool = False
    # 网络搜索间隔（轮数），0 表示禁用自动搜索
    search_interval: int = 5

    def __post_init__(self):
        """初始化后处理：配置工具智能体"""
        # 如果启用工具，为两个智能体设置共享的 ToolAgent
        if self.enable_tools:
            from mind.tools import ToolAgent

            # 创建共享的 ToolAgent 实例
            tool_agent = ToolAgent()

            # 为两个智能体设置同一个工具实例
            self.agent_a.tool_agent = tool_agent
            self.agent_b.tool_agent = tool_agent
            logger.info("工具扩展已启用，两个智能体共享 ToolAgent")

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

    async def run_auto(self, topic: str, max_turns: int = 500) -> str:
        """非交互式自动运行对话

        Args:
            topic: 对话主题
            max_turns: 最大对话轮数

        Returns:
            对话输出文本
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
        self.memory.add_message(topic_msg["role"], cast(str, topic_msg["content"]))
        logger.info(f"非交互式对话开始，主题: {topic}")

        # 收集输出
        output = []
        output.append(f"🎯 **对话主题**: {topic}")
        output.append("")
        output.append("---")
        output.append("")

        # 主对话循环
        for _ in range(max_turns):
            if not self.is_running:
                break

            current_agent = self.agent_a if self.current == 0 else self.agent_b

            output.append(f"### [{current_agent.name}]")
            response = await current_agent.respond(self.messages, self.interrupt)

            if response is not None:
                # 移除可能的前缀
                patterns_to_remove = [
                    rf"^\[{re.escape(current_agent.name)}\]:\s*",
                    rf"^\[{re.escape(current_agent.name)}]\uFF1A\s*",
                    rf"^\*\*{re.escape(current_agent.name)}\uFF1A\*\*\s*",
                    rf"^\*\*{re.escape(current_agent.name)}:\*\*\s*",
                    rf"^{re.escape(current_agent.name)}\uFF1A\s*",
                    rf"^\[{re.escape(current_agent.name)}\]\s*\*\*{re.escape(current_agent.name)}\uFF1A\*\*\s*",
                ]
                for pattern in patterns_to_remove:
                    response = re.sub(pattern, "", response, count=1).lstrip()

                output.append(response)
                output.append("")

                formatted_content = f"[{current_agent.name}]: {response}"
                msg = cast(
                    MessageParam,
                    {"role": "assistant", "content": formatted_content},
                )
                self.messages.append(msg)
                self.memory.add_message(msg["role"], cast(str, msg["content"]))
                self.turn += 1
                logger.debug(f"轮次 {self.turn}: {current_agent.name} 响应完成")

                # 检查记忆状态并在必要时清理
                status = self.memory.get_status()
                if status == "red":
                    self._trim_count += 1
                    logger.warning(
                        f"Token 超限 (第 {self._trim_count} 次)，开始清理对话历史..."
                    )
                    old_count = len(self.messages)
                    self.messages = cast(
                        list[MessageParam],
                        self.memory.trim_messages(cast(list[dict], self.messages)),
                    )
                    new_count = len(self.messages)
                    logger.info(
                        f"清理完成: {old_count} → {new_count} 条消息, "
                        f"{self.memory._total_tokens} tokens"
                    )

                    # 检查是否需要自动退出
                    if self.should_exit_after_trim():
                        self.summary = await self._summarize_conversation()
                        output.append("")
                        output.append("---")
                        output.append("")
                        output.append("⚠️ 对话结束（上下文超限）")
                        output.append("")
                        output.append("📝 **对话总结**")
                        output.append(self.summary)
                        break
            else:
                logger.debug(f"轮次 {self.turn}: {current_agent.name} 响应被中断")

            # 切换到下一个智能体
            self.current = 1 - self.current

        # 添加统计和结尾
        output.append("")
        output.append("---")
        output.append("")
        output.append(
            f"📊 **统计**: {self.turn} 轮对话, {self.memory._total_tokens} tokens"
        )

        # 保存对话到文件
        self.save_conversation()
        logger.info("非交互式对话完成")

        return "\n".join(output)

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

    async def _wait_for_user_input(self):
        """后台等待用户输入，设置中断标志

        这个方法在后台运行，定期检查 stdin 是否有输入可读。
        如果检测到输入，立即设置 interrupt 标志以中断正在进行的响应。
        """
        try:
            while True:
                if _is_input_ready():
                    # 检测到输入，设置中断标志
                    self.interrupt.set()
                    logger.debug("后台监听检测到用户输入，已设置中断标志")
                    break
                # 每 50ms 检查一次
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            # 任务被取消是正常的（当响应完成时）
            logger.debug("输入监听任务被取消")
            raise

    def _extract_search_query(self) -> str | None:
        """从对话历史中提取搜索关键词

        Returns:
            搜索关键词，如果无法提取返回 None
        """
        # 如果没有对话历史，返回 None
        if not self.messages:
            return None

        # 优先使用最近的用户消息
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    # 简单清理：去除明显的对话标记
                    # 移除 / 命令前缀
                    clean_query = content.strip()
                    # 移除常见的命令前缀
                    for prefix in ["/quit", "/exit", "/clear"]:
                        if clean_query.startswith(prefix):
                            clean_query = ""
                            break

                    if clean_query:
                        # 限制关键词长度
                        return clean_query[:100]

        # 如果没有用户消息，使用对话主题
        if self.topic:
            return self.topic[:100]

        # 从最近的助手回复中提取关键词
        for msg in reversed(self.messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    # 简单提取：取前几个有意义的词
                    words = content.strip().split()[:5]
                    if words:
                        return " ".join(words)[:100]

        return None

    # 搜索请求标记模式
    _SEARCH_REQUEST_PATTERN = re.compile(r"\[搜索:\s*([^\]]+)\]")

    # 不确定性关键词
    _UNCERTAINTY_KEYWORDS = [
        "我不确定",
        "不清楚",
        "不确定",
        "未知",
        "最新",
        "当前",
        "具体数据",
        "发布时间",
        "是否已经",
        "最新进展",
        "最近消息",
    ]

    def _has_search_request(self, response: str) -> bool:
        """检测 AI 响应中是否包含搜索请求

        Args:
            response: AI 的响应文本

        Returns:
            是否包含搜索请求
        """
        if not response:
            return False
        return bool(self._SEARCH_REQUEST_PATTERN.search(response))

    def _extract_search_from_response(self, response: str) -> str | None:
        """从 AI 响应中提取搜索关键词

        Args:
            response: AI 的响应文本

        Returns:
            搜索关键词，如果没有找到返回 None
        """
        if not response:
            return None
        match = self._SEARCH_REQUEST_PATTERN.search(response)
        return match.group(1).strip() if match else None

    def _should_search_by_keywords(self) -> bool:
        """通过关键词检测判断是否需要搜索

        Returns:
            是否应该触发搜索
        """
        # 检查最近的对话内容
        recent_messages = (
            self.messages[-3:] if len(self.messages) >= 3 else self.messages
        )

        # 提取字符串内容并拼接
        content_parts: list[str] = []
        for m in recent_messages:
            content = m.get("content", "")
            if isinstance(content, str):
                content_parts.append(content)

        recent_content = " ".join(content_parts)

        # 检查是否包含不确定性关键词
        for keyword in self._UNCERTAINTY_KEYWORDS:
            if keyword in recent_content:
                logger.debug(f"检测到不确定性关键词: {keyword}")
                return True

        return False

    def _should_trigger_search(self, last_response: str | None = None) -> bool:
        """综合判断是否应该触发搜索

        优先级：
        1. AI 主动请求（最高优先级）
        2. 关键词检测
        3. 固定间隔（兜底）

        Args:
            last_response: 最近的 AI 响应（用于检测主动请求）

        Returns:
            是否应该触发搜索
        """
        # 1. 检查 AI 是否主动请求
        if last_response and self._has_search_request(last_response):
            logger.info("AI 主动请求搜索")
            return True

        # 2. 关键词检测
        if self._should_search_by_keywords():
            logger.info("检测到需要外部信息的关键词")
            return True

        # 3. 固定间隔兜底（仅在启用搜索时）
        if (
            self.enable_search
            and self.search_interval > 0
            and self.turn > 0
            and self.turn % self.search_interval == 0
        ):
            logger.info(f"达到搜索间隔: 第 {self.turn} 轮")
            return True

        return False

    async def _turn(self):
        """执行一轮对话"""
        # 确定当前发言的智能体
        current_agent = self.agent_a if self.current == 0 else self.agent_b

        # 工具调用：在特定轮次调用工具并注入结果
        if (
            self.enable_tools
            and self.tool_interval > 0
            and self.turn > 0
            and self.turn % self.tool_interval == 0
        ):
            logger.info(f"第 {self.turn} 轮：调用工具获取上下文")
            print(
                f"\n🔧 [工具调用] 第 {self.turn} 轮：正在分析对话历史...",
                end="",
                flush=True,
            )

            # 调用当前智能体的工具，传入对话历史
            tool_result = await current_agent.query_tool("总结当前对话", self.messages)

            # 如果工具返回有效结果，注入到对话历史
            if tool_result:
                print(" ✅")
                tool_message = cast(
                    MessageParam,
                    {
                        "role": "user",
                        "content": f"[系统消息 - 上下文更新]\n{tool_result}",
                    },
                )
                self.messages.append(tool_message)
                self.memory.add_message(
                    tool_message["role"], cast(str, tool_message["content"])
                )
                logger.info(f"工具结果已注入对话历史，当前消息数: {len(self.messages)}")
            else:
                print(" ⚠️ (无结果)")
                logger.warning(f"第 {self.turn} 轮工具调用未返回有效结果")

        # 智能网络搜索触发（关键词检测 + 固定间隔兜底）
        # 注意：AI 主动请求的搜索在响应处理之后检测
        if self._should_trigger_search():
            # 从对话历史中提取搜索关键词
            search_query = self._extract_search_query()

            if search_query:
                logger.info(f"第 {self.turn} 轮：触发网络搜索")
                print(
                    f"\n🌐 [网络搜索] 第 {self.turn} 轮：正在搜索 '{search_query}'...",
                    end="",
                    flush=True,
                )

                # 导入搜索函数（避免循环导入）
                from mind.tools.search_tool import search_web

                # 执行搜索
                search_result = await search_web(search_query, max_results=3)

                # 如果搜索返回有效结果，注入到对话历史
                if search_result:
                    print(" ✅")
                    search_message = cast(
                        MessageParam,
                        {
                            "role": "user",
                            "content": f"[系统消息 - 网络搜索结果]\n{search_result}",
                        },
                    )
                    self.messages.append(search_message)
                    self.memory.add_message(
                        search_message["role"], cast(str, search_message["content"])
                    )
                    logger.info(
                        f"搜索结果已注入对话历史，当前消息数: {len(self.messages)}"
                    )
                else:
                    print(" ⚠️ (无结果)")
                    logger.warning(f"第 {self.turn} 轮网络搜索未返回有效结果")

        # 打印智能体名称（换行以避免覆盖进度条）
        print(f"\n[{current_agent.name}]: ", end="", flush=True)

        # 创建输入监听任务，在后台并发运行
        input_monitor_task = asyncio.create_task(self._wait_for_user_input())

        # 智能体响应（与输入监听并发执行）
        try:
            response = await current_agent.respond(self.messages, self.interrupt)
        finally:
            # 响应完成（无论成功还是中断），取消输入监听任务
            input_monitor_task.cancel()
            try:
                await input_monitor_task
            except asyncio.CancelledError:
                pass  # 任务取消异常是预期的

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

            # 检查 AI 响应中是否包含搜索请求（最高优先级）
            if self._has_search_request(response):
                # 从响应中提取搜索关键词
                search_query = self._extract_search_from_response(response)

                if search_query:
                    logger.info(f"AI 主动请求搜索: {search_query}")
                    print(
                        f"\n🔍 [AI 请求] 正在搜索 '{search_query}'...",
                        end="",
                        flush=True,
                    )

                    # 导入搜索函数（避免循环导入）
                    from mind.tools.search_tool import search_web

                    # 执行搜索
                    search_result = await search_web(search_query, max_results=3)

                    # 如果搜索返回有效结果，注入到对话历史
                    if search_result:
                        print(" ✅")
                        search_message = cast(
                            MessageParam,
                            {
                                "role": "user",
                                "content": (
                                    f"[系统消息 - 网络搜索结果]\n{search_result}"
                                ),
                            },
                        )
                        self.messages.append(search_message)
                        self.memory.add_message(
                            search_message["role"],
                            cast(str, search_message["content"]),
                        )
                        logger.info(
                            f"AI 请求的搜索结果已注入，当前消息数: {len(self.messages)}"
                        )

                        # 重新生成响应（基于搜索结果）
                        print(f"\n[{current_agent.name}]: ", end="", flush=True)
                        response = await current_agent.respond(
                            self.messages, self.interrupt
                        )
                        if response:
                            print()  # 换行
                            # 再次清理角色名前缀
                            for pattern in patterns_to_remove:
                                response = re.sub(
                                    pattern, "", response, count=1
                                ).lstrip()
                    else:
                        print(" ⚠️ (无结果)")
                        logger.warning("AI 请求的搜索未返回有效结果")

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
