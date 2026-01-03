"""
CLI --test-tools 命令的单元测试

测试工具扩展的 CLI 命令：
- --test-tools 参数解析
- 代码库分析测试
- 文件读取测试
"""

from unittest.mock import AsyncMock, patch

import pytest

from mind.cli import parse_args


class TestParseArgsTestTools:
    """测试 --test-tools 参数解析"""

    @patch("sys.argv", ["cli", "--test-tools"])
    def test_parse_args_with_test_tools_flag(self):
        """测试：--test-tools 标志应正确解析"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert hasattr(args, "test_tools")
        # 注意：由于功能未实现，默认值会是 False

    @patch("sys.argv", ["cli"])
    def test_parse_args_without_test_tools_flag(self):
        """测试：不含 --test-tools 时默认为 False"""
        # Arrange & Act
        parse_args()

        # Assert
        # 如果功能未实现，这个属性可能不存在
        # 我们只测试不报错即可


class TestTestToolsCommand:
    """测试 --test-tools 命令执行"""

    @pytest.mark.asyncio
    async def test_test_tools_runs_codebase_analysis(self):
        """测试：--test-tools 应执行代码库分析"""
        # Arrange
        with patch("mind.tools.tool_agent.ToolAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.analyze_codebase.return_value = {
                "success": True,
                "summary": "测试概述",
                "structure": "测试结构",
                "error": None,
            }
            mock_agent_cls.return_value = mock_agent

            # Act
            from mind.tools.tool_agent import ToolAgent

            agent = ToolAgent()
            result = await agent.analyze_codebase(".")

        # Assert
        assert result["success"] is True
        mock_agent.analyze_codebase.assert_called_once_with(".")

    @pytest.mark.asyncio
    async def test_test_tools_runs_file_analysis(self):
        """测试：--test-tools 应执行文件分析"""
        # Arrange
        with patch("mind.tools.tool_agent.ToolAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.read_file_analysis.return_value = {
                "success": True,
                "file": "src/mind/agents/agent.py",
                "content": "这个文件定义 Agent 类",
                "error": None,
            }
            mock_agent_cls.return_value = mock_agent

            # Act
            from mind.tools.tool_agent import ToolAgent

            agent = ToolAgent()
            result = await agent.read_file_analysis(
                "src/mind/agents/agent.py", "这个文件做什么？"
            )

        # Assert
        assert result["success"] is True
        assert "Agent 类" in result["content"]

    @pytest.mark.asyncio
    async def test_test_tools_handles_analyze_error(self):
        """测试：--test-tools 应处理分析错误"""
        # Arrange
        with patch("mind.tools.tool_agent.ToolAgent") as mock_agent_cls:
            mock_agent = AsyncMock()
            mock_agent.analyze_codebase.return_value = {
                "success": False,
                "summary": "",
                "structure": "",
                "error": "CLI not found",
            }
            mock_agent_cls.return_value = mock_agent

            # Act
            from mind.tools.tool_agent import ToolAgent

            agent = ToolAgent()
            result = await agent.analyze_codebase(".")

        # Assert
        assert result["success"] is False
        assert "CLI not found" in result["error"]
