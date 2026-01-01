"""
CLI --with-tools 参数的单元测试

测试 CLI 的工具参数：
- --with-tools 参数解析
- 参数传递到 ConversationManager
"""

from unittest.mock import patch

from mind.cli import parse_args


class TestParseArgsWithTools:
    """测试 --with-tools 参数解析"""

    @patch("sys.argv", ["cli", "--with-tools"])
    def test_parse_args_with_with_tools_flag(self):
        """测试：--with-tools 标志应正确解析"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert hasattr(args, "with_tools")
        assert args.with_tools is True

    @patch("sys.argv", ["cli"])
    def test_parse_args_without_with_tools_flag(self):
        """测试：不含 --with-tools 时默认为 False"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert hasattr(args, "with_tools")
        assert args.with_tools is False

    @patch("sys.argv", ["cli", "--with-tools", "主题内容"])
    def test_parse_args_with_tools_and_topic(self):
        """测试：--with-tools 可以和主题一起使用"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert args.with_tools is True
        assert args.topic == "主题内容"

    @patch("sys.argv", ["cli", "--with-tools", "--non-interactive"])
    def test_parse_args_with_tools_and_non_interactive(self):
        """测试：--with-tools 可以和 --non-interactive 一起使用"""
        # Arrange & Act
        args = parse_args()

        # Assert
        assert args.with_tools is True
        assert args.non_interactive is True
