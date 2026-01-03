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
from typing import TYPE_CHECKING

from anthropic.types import MessageParam
from rich.console import Console

from mind.agents.agent import Agent
from mind.conversation.ending_detector import (
    ConversationEndConfig,
    ConversationEndDetector,
)
from mind.conversation.memory import MemoryManager
from mind.logger import get_logger

if TYPE_CHECKING:
    from mind.agents.summarizer import SummarizerAgent
    from mind.conversation.flow import FlowController
    from mind.tools.search_history import SearchHistory

logger = get_logger("mind.conversation")

# 对话记忆保存目录
MEMORY_DIR = Path("history")

# Rich console 用于进度条显示
console = Console()


def _is_input_ready():
    """检查是否有输入可读（非阻塞）

    只在交互终端（TTY）中工作，非 TTY 环境返回 False
    """
    # 检查是否在交互终端中运行
    if not sys.stdin.isatty():
        return False
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
    # 搜索历史管理器（每个对话会话独立）
    search_history: "SearchHistory | None" = field(default=None)
    # 对话结束检测器
    end_detector: ConversationEndDetector = field(
        default_factory=lambda: ConversationEndDetector(
            ConversationEndConfig(require_confirmation=True)
        )
    )
    # 总结智能体（专门用于总结对话）
    summarizer_agent: "SummarizerAgent | None" = field(default=None)
    # 流程控制器（延迟初始化）
    _flow_controller: "FlowController | None" = field(default=None, init=False)

    def __post_init__(self):
        """初始化后处理：配置工具智能体"""
        # 初始化搜索历史（每个会话独立）
        if self.enable_search:
            from mind.tools.search_history import SearchHistory

            # 使用时间戳创建会话专属的搜索历史文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = MEMORY_DIR / f"search_history_{timestamp}.json"
            self.search_history = SearchHistory(file_path=history_path)

            # 为两个智能体设置同一个搜索历史实例
            self.agent_a.search_history = self.search_history  # type: ignore[assignment]
            self.agent_b.search_history = self.search_history  # type: ignore[assignment]
            logger.info(f"搜索历史已初始化: {history_path}")

        # 如果启用工具，为两个智能体设置共享的 ToolAgent
        if self.enable_tools:
            from mind.tools import ToolAgent

            # 创建共享的 ToolAgent 实例
            tool_agent = ToolAgent()

            # 为两个智能体设置同一个工具实例
            self.agent_a.tool_agent = tool_agent
            self.agent_b.tool_agent = tool_agent
            logger.info("工具扩展已启用，两个智能体共享 ToolAgent")

        # 初始化总结智能体（从配置加载）
        from mind.agents.summarizer import SummarizerAgent
        from mind.config import get_default_config_path, load_agent_configs

        config_path = get_default_config_path()
        agent_configs = load_agent_configs(str(config_path))
        summarizer_config = agent_configs["summarizer"]

        self.summarizer_agent = SummarizerAgent(
            name=summarizer_config.name,
            system_prompt=summarizer_config.system_prompt,
        )
        logger.info("总结智能体已初始化")

    @property
    def flow_controller(self) -> "FlowController":
        """获取流程控制器（延迟初始化）"""
        if self._flow_controller is None:
            from mind.conversation.flow import FlowController

            self._flow_controller = FlowController(self)
        return self._flow_controller

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

        使用专门的总结智能体对整体对话进行总结。

        Returns:
            对话总结文本
        """
        if not self.summarizer_agent:
            logger.warning("总结智能体未初始化")
            return "对话总结功能不可用"

        try:
            summary = await self.summarizer_agent.summarize(
                messages=self.messages,
                topic=self.topic,
                interrupt=asyncio.Event(),
            )
            return summary
        except Exception as e:
            logger.exception(f"生成对话总结失败: {e}")
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
        # 委托给 FlowController
        await self.flow_controller.start(topic)

    async def run_auto(self, topic: str, max_turns: int = 500) -> str:
        """非交互式自动运行对话

        Args:
            topic: 对话主题
            max_turns: 最大对话轮数

        Returns:
            对话输出文本
        """
        # 委托给 FlowController（支持工具调用）
        # FlowController 的 run_auto 已包含完整实现
        return await self.flow_controller.run_auto(topic, max_turns)

    async def _input_mode(self):
        """输入模式 - 等待用户输入（委托给 InteractionHandler）"""
        handler = self.flow_controller.interaction_handler
        await handler.input_mode()

    async def _wait_for_user_input(self):
        """后台等待用户输入（委托给 InteractionHandler）"""
        handler = self.flow_controller.interaction_handler
        await handler.wait_for_user_input()

    def _extract_search_query(self) -> str | None:
        """从对话历史中提取搜索关键词（委托给 SearchHandler）"""
        return self.flow_controller.search_handler.extract_search_query()

    # 搜索请求标记模式
    _SEARCH_REQUEST_PATTERN = re.compile(r"\[搜索:\s*([^\]]+)\]")

    def _has_search_request(self, response: str) -> bool:
        """检测 AI 响应中是否包含搜索请求（委托给 SearchHandler）"""
        return self.flow_controller.search_handler.has_search_request(response)

    def _extract_search_from_response(self, response: str) -> str | None:
        """从 AI 响应中提取搜索关键词（委托给 SearchHandler）"""
        return self.flow_controller.search_handler.extract_search_from_response(
            response
        )

    def _should_trigger_search(self, last_response: str | None = None) -> bool:
        """判断是否应该触发搜索（委托给 SearchHandler）

        触发条件（按优先级）：
        1. AI 主动请求（使用 [搜索: 关键词] 语法）
        2. 固定间隔（作为兜底）

        AI 通过提示词指导何时使用搜索功能，而不是硬编码规则。

        Args:
            last_response: 最近的 AI 响应（用于检测主动请求）

        Returns:
            是否应该触发搜索
        """
        return self.flow_controller.search_handler.should_trigger_search(last_response)

    async def _turn(self):
        """执行一轮对话（委托给 FlowController）"""
        await self.flow_controller._turn()

    async def _handle_user_input(self, user_input: str):
        """处理用户输入（委托给 InteractionHandler）"""
        handler = self.flow_controller.interaction_handler
        await handler.handle_user_input(user_input)

    async def _handle_end_proposal(self, agent_name: str, response: str) -> None:
        """处理 AI 的对话结束提议（委托给 EndingHandler）

        Args:
            agent_name: 请求结束的智能体名称
            response: 完整响应（包含结束标记）
        """
        handler = self.flow_controller.ending_handler
        await handler.handle_proposal(agent_name, response)
