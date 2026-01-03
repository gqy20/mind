"""
CLI 模块的单元测试

测试命令行界面的功能：
- 配置检查
- 智能体创建
- 主程序流程
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mind.cli import check_config, main
from mind.config import get_default_config_path, load_agent_configs


class TestCheckConfig:
    """测试配置检查功能"""

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_check_config_with_valid_api_key(self, capsys):
        """测试：有效的 API Key 应返回 True"""
        # Arrange & Act
        result = check_config()
        captured = capsys.readouterr()

        # Assert
        assert result is True
        assert "✅ 已设置" in captured.out
        assert "test-key" not in captured.out  # 不泄露 key

    @patch.dict("os.environ", {}, clear=True)
    def test_check_config_without_api_key(self, capsys):
        """测试：缺少 API Key 应返回 False"""
        # Arrange & Act
        result = check_config()
        captured = capsys.readouterr()

        # Assert
        assert result is False
        assert "❌ 未设置" in captured.out
        assert "ANTHROPIC_API_KEY" in captured.out

    @patch.dict(
        "os.environ",
        {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_BASE_URL": "https://api.test.com"},
    )
    def test_check_config_with_custom_base_url(self, capsys):
        """测试：自定义 Base URL 应显示"""
        # Arrange & Act
        result = check_config()
        captured = capsys.readouterr()

        # Assert
        assert result is True
        assert "https://api.test.com" in captured.out


class TestMain:
    """测试主程序流程"""

    @patch("mind.cli.check_config")
    @patch("mind.cli.Agent")
    @patch("mind.cli.ConversationManager")
    @patch("mind.cli.input")
    @pytest.mark.asyncio
    async def test_main_exits_when_config_invalid(
        self, mock_input, mock_manager, mock_agent, mock_check_config
    ):
        """测试：配置无效时应提前退出"""
        # Arrange
        mock_check_config.return_value = False

        # Act
        await main()

        # Assert
        mock_agent.assert_not_called()
        mock_manager.assert_not_called()

    @patch("mind.cli.check_config")
    @patch("mind.agents.AgentFactory")
    @patch("mind.cli.ConversationManager")
    @patch("mind.cli.input")
    @pytest.mark.asyncio
    async def test_main_creates_agents_and_manager(
        self, mock_input, mock_manager, mock_factory, mock_check_config
    ):
        """测试：应创建两个智能体和对话管理器"""
        # Arrange
        mock_check_config.return_value = True
        mock_input.return_value = "测试主题"
        mock_agent_instance = MagicMock()
        mock_factory_instance = MagicMock()
        mock_factory_instance.create_conversation_agents.return_value = {
            "supporter": mock_agent_instance,
            "challenger": mock_agent_instance,
        }
        mock_factory.return_value = mock_factory_instance
        mock_manager_instance = AsyncMock()
        mock_manager.return_value = mock_manager_instance

        # Act
        await main()

        # Assert
        mock_factory.assert_called_once()
        mock_factory_instance.create_conversation_agents.assert_called_once()
        mock_manager.assert_called_once()
        mock_manager_instance.start.assert_called_once_with("测试主题")

    @patch("mind.cli.check_config")
    @patch("mind.cli.Agent")
    @patch("mind.cli.ConversationManager")
    @patch("mind.cli.input")
    @pytest.mark.asyncio
    async def test_main_uses_default_topic_when_empty(
        self, mock_input, mock_manager, mock_agent, mock_check_config
    ):
        """测试：空主题应使用默认值"""
        # Arrange
        mock_check_config.return_value = True
        mock_input.return_value = ""  # 空输入
        mock_manager_instance = AsyncMock()
        mock_manager.return_value = mock_manager_instance

        # Act
        await main()

        # Assert
        mock_manager_instance.start.assert_called_once()
        # 获取调用的参数
        call_args = mock_manager_instance.start.call_args
        topic = call_args[0][0] if call_args[0] else call_args[1].get("topic", "")
        assert "人工智能是否应该拥有法律人格" in topic


class TestPromptsConfig:
    """测试提示词配置加载"""

    def test_get_default_config_path(self):
        """测试：默认配置文件路径应正确"""
        # Arrange & Act
        path = get_default_config_path()

        # Assert
        assert path.name == "prompts.yaml"
        assert "mind" in path.parts

    def test_load_default_config_succeeds(self):
        """测试：应能从默认路径加载配置"""
        # Arrange & Act
        config_path = str(get_default_config_path())
        configs = load_agent_configs(config_path)

        # Assert
        assert "supporter" in configs
        assert "challenger" in configs
        assert "summarizer" in configs  # 新增：验证 summarizer 配置
        assert configs["supporter"].name == "支持者"
        assert configs["challenger"].name == "挑战者"
        assert configs["summarizer"].name == "总结助手"  # 新增：验证总结助手
        # 验证 system_prompt 不为空
        assert configs["supporter"].system_prompt
        assert configs["challenger"].system_prompt
        assert configs["summarizer"].system_prompt
