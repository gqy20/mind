"""
ToolAgent 类的单元测试

测试工具智能体的基本功能：
- 初始化配置
- 代码库分析
- 文件读取分析
- 错误处理
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.tools.tool_agent import ToolAgent, ToolAgentError


class TestToolAgentInit:
    """测试 ToolAgent 初始化"""

    def test_init_with_default_params(self):
        """测试：使用默认参数初始化 ToolAgent"""
        # Arrange & Act
        agent = ToolAgent()

        # Assert
        assert agent.options is not None
        assert agent.options.allowed_tools == ["Read", "Grep"]
        assert agent.options.permission_mode == "default"

    def test_init_with_custom_tools(self):
        """测试：使用自定义工具列表初始化"""
        # Arrange & Act
        agent = ToolAgent(allowed_tools=["Read", "Write", "Bash"])

        # Assert
        assert agent.options.allowed_tools == ["Read", "Write", "Bash"]

    def test_init_with_work_dir(self):
        """测试：使用工作目录初始化"""
        # Arrange & Act
        agent = ToolAgent(work_dir="/tmp/test")

        # Assert
        assert agent.options.cwd == "/tmp/test"


class TestToolAgentAnalyzeCodebase:
    """测试代码库分析功能"""

    @pytest.mark.asyncio
    async def test_analyze_codebase_returns_success_result(self):
        """测试：analyze_codebase 应返回成功结果"""
        # Arrange
        agent = ToolAgent()

        # Mock ClaudeSDKClient
        mock_response = """
        代码库概述：
        - 这是一个 Python 项目
        - 使用 pytest 进行测试
        - 主要模块：agent, conversation, cli
        """

        with patch.object(agent, "_execute", return_value=mock_response):
            # Act
            result = await agent.analyze_codebase(".")

        # Assert
        assert result["success"] is True
        assert result["summary"] == mock_response
        assert result["structure"] == mock_response[:200]
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_analyze_codebase_handles_error(self):
        """测试：analyze_codebase 应处理执行错误"""
        # Arrange
        agent = ToolAgent()

        with patch.object(agent, "_execute", side_effect=Exception("CLI not found")):
            # Act
            result = await agent.analyze_codebase(".")

        # Assert
        assert result["success"] is False
        assert result["summary"] == ""
        assert result["structure"] == ""
        assert "CLI not found" in result["error"]


class TestToolAgentReadFileAnalysis:
    """测试文件读取分析功能"""

    @pytest.mark.asyncio
    async def test_read_file_analysis_returns_content(self):
        """测试：read_file_analysis 应返回文件内容分析"""
        # Arrange
        agent = ToolAgent()

        mock_response = "这个文件定义了 Agent 类，用于 AI 对话。"

        with patch.object(agent, "_execute", return_value=mock_response):
            # Act
            result = await agent.read_file_analysis(
                "src/mind/agents/agent.py", "这个文件做什么？"
            )

        # Assert
        assert result["success"] is True
        assert result["file"] == "src/mind/agents/agent.py"
        assert result["content"] == mock_response
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_read_file_analysis_handles_error(self):
        """测试：read_file_analysis 应处理文件不存在错误"""
        # Arrange
        agent = ToolAgent()

        with patch.object(
            agent, "_execute", side_effect=ToolAgentError("File not found")
        ):
            # Act
            result = await agent.read_file_analysis("nonexistent.py")

        # Assert
        assert result["success"] is False
        assert result["content"] == ""
        assert "File not found" in result["error"]


class TestToolAgentExecute:
    """测试内部 _execute 方法"""

    @pytest.mark.asyncio
    async def test_execute_calls_claude_sdk_client(self):
        """测试：_execute 应调用 ClaudeSDKClient"""
        # Arrange
        agent = ToolAgent()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="测试响应")]
        from claude_agent_sdk.types import AssistantMessage, TextBlock

        mock_message.__class__ = AssistantMessage
        mock_message.content[0].__class__ = TextBlock

        async def mock_receive():
            yield mock_message
            # ResultMessage to stop iteration
            from claude_agent_sdk.types import ResultMessage

            result_msg = ResultMessage(
                subtype="success",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test",
                total_cost_usd=0.001,
            )
            yield result_msg

        mock_client.receive_response = mock_receive
        mock_client.query = AsyncMock()

        with patch("mind.tools.tool_agent.ClaudeSDKClient", return_value=mock_client):
            # Act
            result = await agent._execute("测试提示")

        # Assert
        assert result == "测试响应"

    @pytest.mark.asyncio
    async def test_execute_raises_tool_agent_error_on_failure(self):
        """测试：_execute 在 SDK 错误时应抛出 ToolAgentError"""
        # Arrange
        agent = ToolAgent()

        mock_client = AsyncMock()
        mock_client.__aenter__.side_effect = RuntimeError("CLI process failed")

        with patch("mind.tools.tool_agent.ClaudeSDKClient", return_value=mock_client):
            # Act & Assert
            with pytest.raises(ToolAgentError, match="工具执行失败"):
                await agent._execute("测试提示")


class TestToolAgentExtractStructure:
    """测试结构提取方法"""

    def test_extract_structure_with_long_text(self):
        """测试：_extract_structure 应截断长文本"""
        # Arrange
        agent = ToolAgent()
        long_text = "a" * 300

        # Act
        result = agent._extract_structure(long_text)

        # Assert
        assert len(result) == 200

    def test_extract_structure_with_short_text(self):
        """测试：_extract_structure 应保留短文本"""
        # Arrange
        agent = ToolAgent()
        short_text = "short"

        # Act
        result = agent._extract_structure(short_text)

        # Assert
        assert result == "short"


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.mark.asyncio
    async def test_quick_analyze(self):
        """测试：quick_analyze 应返回分析结果"""
        # Arrange
        mock_result = {
            "success": True,
            "summary": "测试",
            "structure": "",
            "error": None,
        }

        with patch("mind.tools.tool_agent.ToolAgent") as mock_agent_cls:
            mock_instance = AsyncMock()
            mock_instance.analyze_codebase.return_value = mock_result
            mock_agent_cls.return_value = mock_instance

            # Act
            from mind.tools.tool_agent import quick_analyze

            result = await quick_analyze(".")

        # Assert
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_quick_read_file(self):
        """测试：quick_read_file 应返回分析结果"""
        # Arrange
        mock_result = {
            "success": True,
            "file": "test.py",
            "content": "内容",
            "error": None,
        }

        with patch("mind.tools.tool_agent.ToolAgent") as mock_agent_cls:
            mock_instance = AsyncMock()
            mock_instance.read_file_analysis.return_value = mock_result
            mock_agent_cls.return_value = mock_instance

            # Act
            from mind.tools.tool_agent import quick_read_file

            result = await quick_read_file("test.py", "问题")

        # Assert
        assert result["content"] == "内容"
