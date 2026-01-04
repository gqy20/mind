"""对话流程控制模块

提供对话循环、自动运行和轮次执行逻辑。
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from anthropic.types import MessageParam
from rich.console import Console

# 导入其他处理器
from mind.conversation.ending import EndingHandler
from mind.conversation.interaction import InteractionHandler
from mind.conversation.search_handler import SearchHandler
from mind.display.progress import ProgressDisplay
from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.agents.agent import Agent

logger = get_logger("mind.conversation.flow")

console = Console()

# 对话记忆保存目录
MEMORY_DIR = Path("history")


class FlowController:
    """对话流程控制器类

    负责协调对话循环、自动运行和单轮执行。

    Attributes:
        manager: ConversationManager 实例的引用
        interaction_handler: 用户交互处理器
        search_handler: 搜索处理器
        ending_handler: 结束处理器
    """

    def __init__(self, manager):
        """初始化流程控制器

        Args:
            manager: ConversationManager 实例，用于访问对话状态
        """
        self.manager = manager
        # 初始化子处理器
        self.interaction_handler = InteractionHandler(manager)
        self.search_handler = SearchHandler(manager)
        self.ending_handler = EndingHandler(manager)

    def is_input_ready(self) -> bool:
        """检查是否有输入可读（非阻塞）

        Returns:
            是否有输入可读
        """
        return InteractionHandler.is_input_ready()

    async def start(self, topic: str):
        """开始对话

        Args:
            topic: 对话主题
        """
        # 标记为交互模式
        self._is_interactive = True

        # 保存主题和开始时间
        self.manager.topic = topic
        self.manager.start_time = datetime.now()

        # 初始化主题
        topic_msg = MessageParam(
            role="user",
            content=f"对话主题：{topic}\n\n请根据你们的角色展开探讨。",
        )
        self.manager.messages.append(topic_msg)
        self.manager.memory.add_message(topic_msg["role"], str(topic_msg["content"]))
        logger.info(f"对话开始，主题: {topic}")

        console.print("\n💡 提示: 按 Enter 打断对话并输入消息，Ctrl+C 退出\n")

        # 主对话循环
        try:
            while self.manager.is_running:
                # 检查用户是否想输入
                if self.is_input_ready():
                    # 读取并丢弃第一行（触发用的 Enter）
                    sys.stdin.readline()
                    # 进入输入模式
                    await self.interaction_handler.input_mode()
                    continue

                # 执行一轮对话
                await self._turn()
                await asyncio.sleep(self.manager.turn_interval)
        except KeyboardInterrupt:
            logger.info("对话被用户中断")
            console.print("\n\n👋 对话已结束")
        finally:
            # 保存对话到文件
            filepath = self.manager.save_conversation()
            console.print(f"📁 对话已保存到: {filepath}")

    def _initialize_output_header(self, topic: str) -> list[str]:
        """初始化输出头部

        Args:
            topic: 对话主题

        Returns:
            头部输出行
        """
        return [
            f"🎯 **对话主题**: {topic}",
            "",
            "---",
            "",
        ]

    async def _initialize_conversation(self, topic: str) -> None:
        """初始化对话主题和开始时间

        Args:
            topic: 对话主题
        """
        self.manager.topic = topic
        self.manager.start_time = datetime.now()

        topic_msg = MessageParam(
            role="user",
            content=f"对话主题：{topic}\n\n请根据你们的角色展开探讨。",
        )
        self.manager.messages.append(topic_msg)
        self.manager.memory.add_message(topic_msg["role"], str(topic_msg["content"]))
        logger.info(f"非交互式对话开始，主题: {topic}")

    async def _process_agent_turn(self, agent) -> tuple[list[str], bool]:
        """处理智能体轮次

        Args:
            agent: 智能体实例

        Returns:
            (输出行列表, 是否应该结束对话)
        """
        output = []
        output.append(f"### [{agent.name}]")

        # 添加轮次标记（用户消息），让大模型知道当前是谁在发言
        next_turn = self.manager.turn + 1
        turn_marker = MessageParam(
            role="user",
            content=f"[轮次 {next_turn}] 现在由 {agent.name} 发言",
        )
        self.manager.messages.append(turn_marker)
        self.manager.memory.add_message(
            turn_marker["role"], str(turn_marker["content"])
        )
        logger.debug(f"轮次 {next_turn}: 切换到 {agent.name}")

        response = await agent.respond(self.manager.messages, self.manager.interrupt)

        if response is None:
            return [], False

        output.append(response)

        # 添加引用行（如果有）
        if hasattr(agent, "_last_citations_lines"):
            citations_lines = agent._last_citations_lines
            if citations_lines:
                output.extend(citations_lines)

        output.append("")

        # 检测对话结束标记（传入 messages 用于智能分析）
        end_result = self.manager.end_detector.detect(
            response, current_turn=next_turn, messages=self.manager.messages
        )
        if end_result.detected:
            logger.info(f"{agent.name} 请求结束对话（非交互式）")
            output.append("")
            output.append("---")
            output.append("")
            output.append("⚠️ AI 请求结束对话")
            return output, True

        # 添加消息到历史（不再添加前缀）
        msg = MessageParam(role="assistant", content=response)
        self.manager.messages.append(msg)
        self.manager.memory.add_message(msg["role"], str(msg["content"]))
        self.manager.turn += 1
        logger.debug(f"轮次 {self.manager.turn}: {agent.name} 响应完成")

        return output, False

    async def _check_memory_trim_needed(self) -> bool:
        """检查是否需要清理记忆

        Returns:
            是否应该退出对话（因为达到最大清理次数）
        """
        status = self.manager.memory.get_status()
        if status == "red":
            self.manager._trim_count += 1
            if self.manager.should_exit_after_trim():
                self.manager.summary = await self.manager._summarize_conversation()
                return True
        return False

    def _format_conversation_output(
        self, topic: str, summary: str | None, turn_count: int, token_count: int
    ) -> list[str]:
        """格式化对话输出

        Args:
            topic: 对话主题
            summary: 对话总结
            turn_count: 轮次数
            token_count: token 数量

        Returns:
            格式化的输出行
        """
        output = []

        # 添加总结（如果有）
        if summary and isinstance(summary, str):
            output.append("")
            output.append("---")
            output.append("")
            output.append("## 📝 对话总结")
            output.append("")
            output.append(summary)

        # 添加统计
        output.append("")
        output.append("---")
        output.append("")
        output.append(f"📊 **统计**: {turn_count} 轮对话, {token_count} tokens")

        return output

    async def run_auto(self, topic: str, max_turns: int = 500) -> str:
        """非交互式自动运行对话

        Args:
            topic: 对话主题
            max_turns: 最大对话轮数

        Returns:
            对话输出文本
        """
        # 标记为非交互模式
        self._is_interactive = False

        # 初始化对话
        await self._initialize_conversation(topic)

        # 收集输出
        output = self._initialize_output_header(topic)

        # 主对话循环
        last_response = None  # 记录上一轮的响应，用于检测搜索请求

        for _ in range(max_turns):
            if not self.manager.is_running:
                break

            current_agent = (
                self.manager.agent_a
                if self.manager.current == 0
                else self.manager.agent_b
            )

            # 检查是否触发搜索（基于上一轮的响应）
            if self.search_handler.should_trigger_search(last_response):
                search_query = self.search_handler.extract_search_query()
                if search_query:
                    # 检查上一轮响应中是否有明确的搜索请求
                    if last_response:
                        explicit_query = (
                            self.search_handler.extract_search_from_response(
                                last_response
                            )
                        )
                        if explicit_query:
                            search_query = explicit_query
                    output.append(await self._execute_search(search_query))
                    # 搜索后清空 last_response，避免重复触发
                    last_response = None
                    continue

            # 执行智能体响应
            turn_output, should_end = await self._process_agent_turn(current_agent)
            output.extend(turn_output)

            if should_end:
                break

            # 提取响应文本（用于检测下一轮的搜索请求）
            # turn_output 格式: ["### [Agent Name]", "response text", "", ...]
            if len(turn_output) >= 2:
                last_response = turn_output[1]  # 第二行是响应文本
            else:
                last_response = None

            # 检查记忆状态
            should_exit = await self._check_memory_trim_needed()
            if should_exit:
                output.append("")
                output.append("---")
                output.append("")
                output.append("⚠️ 对话结束（上下文超限）")
                break

            # 切换到下一个智能体
            self.manager.current = 1 - self.manager.current

        # 对话结束后生成总结（无论是正常结束还是因上下文超限）
        if not self.manager.summary:
            self.manager.summary = await self.manager._summarize_conversation()

        # 格式化输出
        summary_output = self._format_conversation_output(
            topic=topic,
            summary=self.manager.summary,
            turn_count=self.manager.turn,
            token_count=self.manager.memory._total_tokens,
        )
        output.extend(summary_output)

        # 保存对话到文件
        self.manager.save_conversation()
        logger.info("非交互式对话完成")

        return "\n".join(output)

    async def _check_and_execute_tools(self, agent) -> None:
        """检查并执行工具调用

        Args:
            agent: 智能体实例
        """
        if (
            self.manager.enable_tools
            and self.manager.tool_interval > 0
            and self.manager.turn % self.manager.tool_interval == 0
            and self.manager.turn > 0
        ):
            tool_result = await agent.query_tool("总结当前对话", self.manager.messages)
            if tool_result:
                # 将工具结果注入到对话历史
                tool_message = MessageParam(
                    role="user",
                    content=f"[上下文更新]\n{tool_result}",
                )
                self.manager.messages.append(tool_message)
                self.manager.memory.add_message(
                    tool_message["role"], str(tool_message["content"])
                )

    async def _handle_ai_search_request(
        self, agent: "Agent", initial_response: str
    ) -> str:
        """处理 AI 搜索请求

        Args:
            agent: 智能体实例
            initial_response: 初始响应（可能包含搜索请求）

        Returns:
            最终响应内容
        """
        if self.search_handler.has_search_request(initial_response):
            search_query = self.search_handler.extract_search_from_response(
                initial_response
            )
            if search_query:
                await self._execute_ai_requested_search(agent, search_query)
                # 重新生成响应
                response = await agent.respond(
                    self.manager.messages, self.manager.interrupt
                )
                if response is not None:
                    console.print()  # 换行
                    return response
                # 如果重新生成被中断，返回初始响应
                return initial_response

        return initial_response

    async def _execute_agent_response(
        self, agent, monitor_input: bool = True
    ) -> str | None:
        """执行智能体响应

        Args:
            agent: 智能体实例
            monitor_input: 是否监听用户输入

        Returns:
            响应内容，如果被中断则返回 None
        """
        # 打印智能体名称
        print(f"\n[{agent.name}]: ", end="", flush=True)

        # 创建输入监听任务
        input_monitor_task = None
        if monitor_input:
            input_monitor_task = asyncio.create_task(
                self.interaction_handler.wait_for_user_input()
            )

        # 智能体响应
        try:
            response = await agent.respond(
                self.manager.messages, self.manager.interrupt
            )
        finally:
            if input_monitor_task:
                input_monitor_task.cancel()
                try:
                    await input_monitor_task
                except asyncio.CancelledError:
                    pass

        console.print()  # 换行

        if response is None:
            return None

        # 处理 AI 主动请求搜索
        response = await self._handle_ai_search_request(agent, response)

        return response

    def _add_agent_message(self, agent, content: str, to_memory: bool = True) -> None:
        """添加智能体消息到对话历史

        不再添加前缀，避免身份混淆。智能体的身份由系统提示词控制。

        Args:
            agent: 智能体实例
            content: 响应内容
            to_memory: 是否添加到记忆
        """
        msg = MessageParam(role="assistant", content=content)
        self.manager.messages.append(msg)

        if to_memory:
            self.manager.memory.add_message(msg["role"], str(msg["content"]))

        self.manager.turn += 1
        logger.debug(f"轮次 {self.manager.turn}: {agent.name} 响应完成")

    async def _turn(self):
        """执行一轮对话"""
        # ========== 处理过渡期 ==========
        # 如果在过渡期，减少计数
        if self.manager.pending_end_count > 0:
            self.manager.pending_end_count -= 1
            logger.debug(
                f"过渡期剩余轮数: {self.manager.pending_end_count}/"
                f"{self.manager.end_detector.config.transition_turns}"
            )

        # 确定当前发言的智能体
        current_agent = (
            self.manager.agent_a if self.manager.current == 0 else self.manager.agent_b
        )

        # 添加轮次标记（用户消息），让大模型知道当前是谁在发言
        next_turn = self.manager.turn + 1
        turn_marker = MessageParam(
            role="user",
            content=f"[轮次 {next_turn}] 现在由 {current_agent.name} 发言",
        )
        self.manager.messages.append(turn_marker)
        self.manager.memory.add_message(
            turn_marker["role"], str(turn_marker["content"])
        )
        logger.debug(f"轮次 {next_turn}: 切换到 {current_agent.name}")

        # 检查是否触发搜索
        if self.search_handler.should_trigger_search():
            search_query = self.search_handler.extract_search_query()
            if search_query:
                await self._execute_search_interactive(search_query)

        # 检查并执行工具调用
        await self._check_and_execute_tools(current_agent)

        # 执行智能体响应
        response = await self._execute_agent_response(current_agent)

        # 如果未被中断，记录响应
        if response is not None:
            # 添加消息到历史（不再添加前缀）
            msg = MessageParam(role="assistant", content=response)
            self.manager.messages.append(msg)
            self.manager.memory.add_message(msg["role"], str(msg["content"]))

            self.manager.turn += 1

            # 显示 token 进度（每轮显示）
            ProgressDisplay.show_token_progress(
                self.manager.memory._total_tokens,
                self.manager.memory.config.max_context,
            )
            console.print()  # 进度后换行

            # 检测对话结束标记（传入 messages 用于智能分析）
            end_result = self.manager.end_detector.detect(
                response, current_turn=self.manager.turn, messages=self.manager.messages
            )
            if end_result.detected:
                if end_result.transition > 0:
                    # 需要过渡轮数
                    self.manager.pending_end_count = end_result.transition
                    # 设置过渡激活标记（用于检测过渡期结束）
                    self.manager._pending_end_active = True
                    logger.info(
                        f"{current_agent.name} 请求结束对话，"
                        f"进入过渡期（{end_result.transition} 轮）"
                    )
                    console.print(
                        f"\n📢 [系统] {current_agent.name} 建议结束对话，"
                        f"将进行 {end_result.transition} 轮过渡对话..."
                    )
                else:
                    # 立即结束（兼容旧行为）
                    logger.info(f"{current_agent.name} 请求结束对话")
                    await self.ending_handler.handle_proposal(
                        current_agent.name, response
                    )
                    return  # 结束本轮

            # 检查记忆状态
            status = self.manager.memory.get_status()
            if status == "red":
                await self._handle_memory_trim()
        else:
            logger.debug(
                f"轮次 {self.manager.turn + 1}: {current_agent.name} 响应被中断"
            )

        # 切换到下一个智能体
        self.manager.current = 1 - self.manager.current

        # ========== 检查过渡期是否结束 ==========
        # 如果 pending_end_count == 0 且之前设置了过渡（通过检查是否被确认标记）
        # 我们需要在过渡期结束后真正结束对话
        if (
            self.manager.pending_end_count == 0
            and hasattr(self.manager, "_pending_end_active")
            and self.manager._pending_end_active
        ):
            # 过渡期结束，真正结束对话
            logger.info("过渡期结束，准备结束对话")
            # 这里会在主循环中被处理，因为 is_running 会被设置
            await self._handle_transition_end()

    async def _handle_transition_end(self):
        """处理过渡期结束

        非交互模式：直接结束
        交互模式：提示用户确认
        """
        # 清除过渡标记
        if hasattr(self.manager, "_pending_end_active"):
            self.manager._pending_end_active = False

        # 非交互模式：直接通过 ending_handler 处理
        if not hasattr(self, "_is_interactive") or not self._is_interactive:
            # 生成总结
            summary = await self.manager._summarize_conversation()
            self.manager.summary = summary
            # 保存对话
            self.manager.save_conversation()
            # 设置结束标志
            self.manager.is_running = False
        else:
            # 交互模式：提示用户确认
            console.print("\n📢 [系统] 过渡期结束，是否确认结束对话？")
            console.print("  按 Enter 确认结束，或输入其他内容继续对话")
            print("> ", end="", flush=True)

            # 获取用户输入
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            except EOFError:
                user_input = ""

            console.print()  # 换行

            if not user_input.strip():
                # 用户确认结束
                logger.info("用户确认结束对话（过渡期结束）")

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
                logger.info("用户选择继续对话（过渡期结束）")

                # 将用户输入添加到对话历史
                msg = MessageParam(role="user", content=user_input)
                self.manager.messages.append(msg)
                self.manager.memory.add_message(msg["role"], str(msg["content"]))

                console.print(f"\n{'=' * 60}")
                console.print("✅ 继续对话...")
                console.print(f"{'=' * 60}\n")

    async def should_trigger_search(self, last_response: str | None = None) -> bool:
        """判断是否应该触发搜索（委托给 SearchHandler）"""
        return self.search_handler.should_trigger_search(last_response)

    async def handle_end_proposal(self, agent_name: str, response: str):
        """处理结束提议（委托给 EndingHandler）"""
        await self.ending_handler.handle_proposal(agent_name, response)

    async def _execute_search(self, query: str) -> str:
        """执行搜索并返回结果消息"""
        from mind.tools.search_tool import search_web

        logger.info(f"第 {self.manager.turn} 轮：触发网络搜索")
        msg = f"\n🌐 [网络搜索] 第 {self.manager.turn} 轮：正在搜索 '{query}'..."

        search_result = await search_web(query, max_results=3)

        if search_result:
            msg += " ✅\n"
            search_message = MessageParam(
                role="user",
                content=f"[系统消息 - 网络搜索结果]\n{search_result}",
            )
            self.manager.messages.append(search_message)
            self.manager.memory.add_message(
                search_message["role"], str(search_message["content"])
            )
        else:
            msg += " ⚠️ (无结果)\n"

        return msg

    async def _process_search_result(self, search_result: str | None, log_prefix: str):
        """处理搜索结果并添加到对话历史

        Args:
            search_result: 搜索结果文本（可能为 None）
            log_prefix: 日志前缀（用于区分不同搜索来源）
        """
        if search_result:
            search_message = MessageParam(
                role="user",
                content=f"[系统消息 - 网络搜索结果]\n{search_result}",
            )
            self.manager.messages.append(search_message)
            self.manager.memory.add_message(
                search_message["role"], str(search_message["content"])
            )
            logger.info(
                f"{log_prefix}结果已注入，当前消息数: {len(self.manager.messages)}"
            )
        else:
            logger.warning(f"{log_prefix}未返回有效结果")

    async def _execute_search_interactive(self, query: str):
        """交互模式下执行搜索"""
        print(
            f"\n🌐 [网络搜索] 第 {self.manager.turn} 轮：正在搜索 '{query}'...",
            end="",
            flush=True,
        )

        from mind.tools.search_tool import search_web

        search_result = await search_web(query, max_results=3)

        if search_result:
            console.print(" ✅")
        else:
            console.print(" ⚠️ (无结果)")

        await self._process_search_result(
            search_result=search_result,
            log_prefix=f"第 {self.manager.turn} 轮网络搜索",
        )

    async def _execute_ai_requested_search(self, agent, query: str):
        """执行 AI 主动请求的搜索"""
        logger.info(f"AI 主动请求搜索: {query}")
        print(
            f"\n🔍 [AI 请求] 正在搜索 '{query}'...",
            end="",
            flush=True,
        )

        from mind.tools.search_tool import search_web

        search_result = await search_web(query, max_results=3)

        if search_result:
            console.print(" ✅")
        else:
            console.print(" ⚠️ (无结果)")

        await self._process_search_result(
            search_result=search_result,
            log_prefix="AI 请求的搜索",
        )

    async def _handle_memory_trim(self):
        """处理记忆清理"""
        self.manager._trim_count += 1
        logger.warning(
            f"Token 超限 (第 {self.manager._trim_count} 次)，开始清理对话历史..."
        )

        old_count = len(self.manager.messages)
        self.manager.messages = list(
            cast(
                list[MessageParam],
                self.manager.memory.trim_messages(
                    cast(list[dict], self.manager.messages)
                ),
            )
        )
        new_count = len(self.manager.messages)
        logger.info(
            f"清理完成: {old_count} → {new_count} 条消息, "
            f"{self.manager.memory._total_tokens} tokens"
        )

        # 检查是否需要自动退出
        if self.manager.should_exit_after_trim():
            console.print(f"\n{'=' * 60}")
            console.print(
                f"⚠️  已达到最大清理次数 "
                f"({self.manager.memory.config.max_trim_count} 次)"
            )
            console.print("正在生成对话总结...")
            console.print(f"{'=' * 60}\n")

            # 生成总结
            self.manager.summary = await self.manager._summarize_conversation()

            console.print(f"\n{'=' * 60}")
            console.print("📝 对话总结")
            console.print(f"{'=' * 60}")
            console.print(f"{self.manager.summary}\n")
            console.print(f"{'=' * 60}")
            console.print("💾 对话已保存（包含总结）")
            console.print(f"{'=' * 60}\n")

            # 标记退出
            self.manager.is_running = False
            logger.info("达到最大清理次数，对话自动结束")
