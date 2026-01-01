"""
CLI --no-tools 参数的单元测试

测试 CLI 的工具参数：
- --no-tools 参数解析
- 默认启用工具
- 参数传递到 ConversationManager
"""

from unittest.mock import patch

from mind.cli import parse_args


class TestParseArgsWithTools:
    """测试 --no-tools 参数解析"""

    @patch("sys.argv", ["cli"])
    def test_parse_args_default_tools_enabled(self):
        """测试：默认启用工具（no_tools=False）"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert hasattr(args, "no_tools")
        assert args.no_tools is False

    @patch("sys.argv", ["cli", "--no-tools"])
    def test_parse_args_with_no_tools_flag(self):
        """测试：--no-tools 标志应正确解析"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert hasattr(args, "no_tools")
        assert args.no_tools is True

    @patch("sys.argv", ["cli", "主题内容"])
    def test_parse_args_with_topic(self):
        """测试：默认启用工具，可以指定主题"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert args.no_tools is False
        assert args.topic == "主题内容"

    @patch("sys.argv", ["cli", "--no-tools", "--non-interactive"])
    def test_parse_args_with_no_tools_and_non_interactive(self):
        """测试：--no-tools 可以和 --non-interactive 一起使用"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert args.no_tools is True
        assert args.non_interactive is True

    @patch("sys.argv", ["cli", "--tool-interval", "10"])
    def test_parse_args_with_tool_interval(self):
        """测试：--tool-interval 参数正确解析"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert args.tool_interval == 10
        assert args.no_tools is False  # 默认仍启用工具
