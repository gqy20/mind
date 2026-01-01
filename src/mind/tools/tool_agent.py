"""
工具智能体模块 - 基于 claude-agent-sdk 的扩展能力

阶段一功能：
- 代码库结构分析
- 文件读取和分析
- 基础错误处理
"""

from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import AssistantMessage, TextBlock

from mind.logger import get_logger

logger = get_logger("mind.tool_agent")


class ToolAgentError(Exception):
    """工具智能体错误"""

    pass


class ToolAgent:
    """工具智能体 - 提供文件和代码操作能力

    阶段一特性：
    - 只读工具（Read, Grep）
    - 单次执行模式
    - 简单的错误处理

    设计原则：
    - 按需创建，用完即销毁
    - 独立会话，不与主对话共享
    - 返回结构化结果
    """

    # 默认允许的工具（只读，安全）
    DEFAULT_TOOLS = ["Read", "Grep"]

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        work_dir: str | Path | None = None,
    ):
        """初始化工具智能体

        Args:
            allowed_tools: 允许使用的工具列表，默认只读工具
            work_dir: 工作目录，默认为当前目录
        """
        if allowed_tools is None:
            allowed_tools = self.DEFAULT_TOOLS.copy()

        self.options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            permission_mode="default",
        )

        if work_dir:
            self.options.cwd = str(work_dir)

        logger.info(f"ToolAgent 初始化, 允许工具: {allowed_tools}")

    async def analyze_codebase(
        self,
        path: str = ".",
    ) -> dict[str, Any]:
        """分析代码库结构

        Args:
            path: 代码库路径

        Returns:
            分析结果字典:
            {
                "success": bool,
                "summary": str,  # 代码库概述
                "structure": str,  # 目录结构
                "error": str | None,  # 错误信息
            }
        """
        prompt = f"""
        请分析当前代码库：{path}

        请提供：
        1. 代码库概述（技术栈、架构模式）
        2. 主要目录结构
        3. 关键文件和它们的职责

        用简洁的中文回答，不超过 500 字。
        """

        try:
            result = await self._execute(prompt)
            return {
                "success": True,
                "summary": result,
                "structure": self._extract_structure(result),
                "error": None,
            }
        except Exception as e:
            logger.error(f"代码库分析失败: {e}")
            return {
                "success": False,
                "summary": "",
                "structure": "",
                "error": str(e),
            }

    async def read_file_analysis(
        self,
        file_path: str,
        question: str = "这个文件做什么？",
    ) -> dict[str, Any]:
        """读取并分析文件

        Args:
            file_path: 文件路径
            question: 要问的问题

        Returns:
            分析结果
        """
        prompt = f"""
        请阅读文件: {file_path}

        然后回答: {question}

        如果需要，可以使用 Read 工具读取文件内容。

        用简洁的中文回答，不超过 300 字。
        """

        try:
            result = await self._execute(prompt)
            return {
                "success": True,
                "file": file_path,
                "content": result,
                "error": None,
            }
        except Exception as e:
            logger.error(f"文件分析失败: {e}")
            return {
                "success": False,
                "file": file_path,
                "content": "",
                "error": str(e),
            }

    async def _execute(self, prompt: str) -> str:
        """执行工具任务并提取文本响应

        Args:
            prompt: 任务提示

        Returns:
            提取的文本内容

        Raises:
            ToolAgentError: 执行失败时抛出
        """
        try:
            async with ClaudeSDKClient(options=self.options) as client:
                await client.query(prompt)

                # 收集所有文本响应
                text_parts = []
                async for msg in client.receive_response():
                    if isinstance(msg, AssistantMessage):
                        for block in msg.content:
                            if isinstance(block, TextBlock):
                                text_parts.append(block.text)

                result = "".join(text_parts).strip()
                logger.info(f"ToolAgent 执行完成, 输出长度: {len(result)}")
                return result

        except Exception as e:
            logger.error(f"ToolAgent 执行异常: {e}", exc_info=True)
            raise ToolAgentError(f"工具执行失败: {e}") from e
        # 此处不可达 (mypy 控制流分析需要)
        raise AssertionError("unreachable")  # noqa: F901

    def _extract_structure(self, analysis: str) -> str:
        """从分析结果中提取目录结构

        Args:
            analysis: 分析文本

        Returns:
            结构化的目录描述
        """
        # 简化版：直接返回前 200 字
        return analysis[:200] if len(analysis) > 200 else analysis


# ============================================================================
# 便捷函数
# ============================================================================


async def quick_analyze(path: str = ".") -> dict[str, Any]:
    """快速分析代码库

    Args:
        path: 代码库路径

    Returns:
        分析结果
    """
    agent = ToolAgent()
    return await agent.analyze_codebase(path)


async def quick_read_file(file_path: str, question: str) -> dict[str, Any]:
    """快速读取文件

    Args:
        file_path: 文件路径
        question: 问题

    Returns:
        分析结果
    """
    agent = ToolAgent()
    return await agent.read_file_analysis(file_path, question)
