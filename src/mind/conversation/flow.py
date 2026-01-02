"""对话流程控制模块

提供对话循环、自动运行和轮次执行逻辑。
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import cast

from anthropic.types import MessageParam
from rich.console import Console

# 导入其他处理器
from mind.conversation.ending import EndingHandler
from mind.conversation.interaction import InteractionHandler
from mind.conversation.progress import ProgressDisplay
from mind.conversation.search_handler import SearchHandler
from mind.logger import get_logger

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

    async def run_auto(self, topic: str, max_turns: int = 500) -> str:
        """非交互式自动运行对话

        Args:
            topic: 对话主题
            max_turns: 最大对话轮数

        Returns:
            对话输出文本
        """
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
        logger.info(f"非交互式对话开始，主题: {topic}")

        # 收集输出
        output = []
        output.append(f"🎯 **对话主题**: {topic}")
        output.append("")
        output.append("---")
        output.append("")

        # 主对话循环
        for _ in range(max_turns):
            if not self.manager.is_running:
                break

            current_agent = (
                self.manager.agent_a
                if self.manager.current == 0
                else self.manager.agent_b
            )

            # 检查是否触发搜索
            if self.search_handler.should_trigger_search():
                search_query = self.search_handler.extract_search_query()
                if search_query:
                    output.append(await self._execute_search(search_query))

            # 执行智能体响应
            output.append(f"### [{current_agent.name}]")
            response = await current_agent.respond(
                self.manager.messages, self.manager.interrupt
            )

            if response is not None:
                output.append(response)
                output.append("")

                # 检测对话结束标记
                end_result = self.manager.end_detector.detect(
                    response, current_turn=self.manager.turn + 1
                )
                if end_result.detected:
                    logger.info(f"{current_agent.name} 请求结束对话（非交互式）")
                    output.append("")
                    output.append("---")
                    output.append("")
                    output.append("⚠️ AI 请求结束对话")
                    break

                formatted_content = f"[{current_agent.name}]: {response}"
                msg = MessageParam(role="assistant", content=formatted_content)
                self.manager.messages.append(msg)
                self.manager.memory.add_message(msg["role"], str(msg["content"]))
                self.manager.turn += 1
                logger.debug(f"轮次 {self.manager.turn}: {current_agent.name} 响应完成")

                # 检查记忆状态
                status = self.manager.memory.get_status()
                if status == "red":
                    self.manager._trim_count += 1
                    if self.manager.should_exit_after_trim():
                        self.manager.summary = (
                            await self.manager._summarize_conversation()
                        )
                        output.append("")
                        output.append("---")
                        output.append("")
                        output.append("⚠️ 对话结束（上下文超限）")
                        break
            else:
                logger.debug(
                    f"轮次 {self.manager.turn}: {current_agent.name} 响应被中断"
                )

            # 切换到下一个智能体
            self.manager.current = 1 - self.manager.current

        # 添加统计和结尾
        output.append("")
        output.append("---")
        output.append("")
        output.append(
            f"📊 **统计**: {self.manager.turn} 轮对话, "
            f"{self.manager.memory._total_tokens} tokens"
        )

        # 保存对话到文件
        self.manager.save_conversation()
        logger.info("非交互式对话完成")

        return "\n".join(output)

    async def _turn(self):
        """执行一轮对话"""
        # 确定当前发言的智能体
        current_agent = (
            self.manager.agent_a if self.manager.current == 0 else self.manager.agent_b
        )

        # 检查是否触发搜索
        if self.search_handler.should_trigger_search():
            search_query = self.search_handler.extract_search_query()
            if search_query:
                await self._execute_search_interactive(search_query)

        # 打印智能体名称
        print(f"\n[{current_agent.name}]: ", end="", flush=True)

        # 创建输入监听任务
        input_monitor_task = asyncio.create_task(
            self.interaction_handler.wait_for_user_input()
        )

        # 智能体响应
        try:
            response = await current_agent.respond(
                self.manager.messages, self.manager.interrupt
            )
        finally:
            input_monitor_task.cancel()
            try:
                await input_monitor_task
            except asyncio.CancelledError:
                pass

        console.print()  # 换行

        # 如果未被中断，记录响应
        if response is not None:
            # 清理响应前缀
            response = self._clean_response_prefix(response, current_agent.name)

            # 检查 AI 主动请求搜索
            if self.search_handler.has_search_request(response):
                search_query = self.search_handler.extract_search_from_response(
                    response
                )
                if search_query:
                    await self._execute_ai_requested_search(current_agent, search_query)
                    # 重新生成响应
                    response = await current_agent.respond(
                        self.manager.messages, self.manager.interrupt
                    )
                    if response:
                        console.print()  # 换行
                        response = self._clean_response_prefix(
                            response, current_agent.name
                        )

            formatted_content = f"[{current_agent.name}]: {response}"
            msg = MessageParam(role="assistant", content=formatted_content)
            self.manager.messages.append(msg)
            self.manager.memory.add_message(msg["role"], str(msg["content"]))
            self.manager.turn += 1
            logger.debug(f"轮次 {self.manager.turn}: {current_agent.name} 响应完成")

            # 显示 token 进度
            if self.manager.turn % 3 == 0:
                ProgressDisplay.show_token_progress(
                    self.manager.memory._total_tokens,
                    self.manager.memory.config.max_context,
                )
                console.print()  # 进度后空行

            # 检测对话结束标记
            end_result = self.manager.end_detector.detect(
                response, current_turn=self.manager.turn + 1
            )
            if end_result.detected:
                logger.info(f"{current_agent.name} 请求结束对话")
                await self.ending_handler.handle_proposal(current_agent.name, response)
                return  # 结束本轮

            # 检查记忆状态
            status = self.manager.memory.get_status()
            if status == "red":
                await self._handle_memory_trim()
        else:
            logger.debug(f"轮次 {self.manager.turn}: {current_agent.name} 响应被中断")

        # 切换到下一个智能体
        self.manager.current = 1 - self.manager.current

    async def should_trigger_search(self, last_response: str | None = None) -> bool:
        """判断是否应该触发搜索（委托给 SearchHandler）"""
        return self.search_handler.should_trigger_search(last_response)

    async def handle_end_proposal(self, agent_name: str, response: str):
        """处理结束提议（委托给 EndingHandler）"""
        await self.ending_handler.handle_proposal(agent_name, response)

    def _clean_response_prefix(self, response: str, agent_name: str) -> str:
        """清理响应中的角色名前缀"""
        patterns_to_remove = [
            rf"^\[{re.escape(agent_name)}\]:\s*",
            rf"^\[{re.escape(agent_name)}]\uFF1A\s*",
            rf"^\*\*{re.escape(agent_name)}\uFF1A\*\*\s*",
            rf"^\*\*{re.escape(agent_name)}:\*\*\s*",
            rf"^{re.escape(agent_name)}\uFF1A\s*",
        ]
        for pattern in patterns_to_remove:
            response = re.sub(pattern, "", response, count=1).lstrip()
        return response

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
            search_message = MessageParam(
                role="user",
                content=f"[系统消息 - 网络搜索结果]\n{search_result}",
            )
            self.manager.messages.append(search_message)
            self.manager.memory.add_message(
                search_message["role"], str(search_message["content"])
            )
            logger.info(
                f"搜索结果已注入对话历史，当前消息数: {len(self.manager.messages)}"
            )
        else:
            console.print(" ⚠️ (无结果)")
            logger.warning(f"第 {self.manager.turn} 轮网络搜索未返回有效结果")

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
            search_message = MessageParam(
                role="user",
                content=f"[系统消息 - 网络搜索结果]\n{search_result}",
            )
            self.manager.messages.append(search_message)
            self.manager.memory.add_message(
                search_message["role"], str(search_message["content"])
            )
            logger.info(
                f"AI 请求的搜索结果已注入，当前消息数: {len(self.manager.messages)}"
            )
        else:
            console.print(" ⚠️ (无结果)")
            logger.warning("AI 请求的搜索未返回有效结果")

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
