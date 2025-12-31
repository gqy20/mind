"""
日志模块的单元测试

测试日志系统的功能：
- 日志配置
- 日志输出到文件
- 日志轮转
- 不同级别的日志记录
"""

import logging
from pathlib import Path

from mind.logger import get_logger, setup_logger


class TestSetupLogger:
    """测试日志配置功能"""

    def test_setup_logger_creates_logger(self):
        """测试：应创建指定名称的 logger"""
        # Arrange & Act
        logger_class = setup_logger("test_logger")

        # Assert - logger 应该有基本方法
        assert hasattr(logger_class, "info")
        assert hasattr(logger_class, "debug")
        assert hasattr(logger_class, "warning")
        assert hasattr(logger_class, "error")
        assert logger_class._name == "test_logger"

    def test_setup_logger_creates_log_file(self, tmp_path):
        """测试：应创建日志文件"""
        # Arrange
        log_dir = tmp_path / "logs"

        # Act - 禁用时间戳以便测试检查固定文件名
        logger = setup_logger(
            name="test_with_file",
            log_to_file=True,
            log_dir=log_dir,
            log_file="test.log",
            use_timestamp=False,
        )
        logger.info("测试消息")

        # Assert
        log_file = log_dir / "test.log"
        assert log_file.exists()

    def test_setup_logger_console_only(self, capsys):
        """测试：仅控制台输出时不创建文件"""
        # Arrange
        import tempfile

        log_dir = Path(tempfile.mkdtemp()) / "logs"

        # Act
        logger = setup_logger(
            name="test_console_only",
            log_to_file=False,
            log_dir=log_dir,
        )
        logger.info("测试消息")

        # Assert - 不应创建日志目录
        assert not log_dir.exists()

    def test_setup_logger_with_different_level(self):
        """测试：不同 logger 应该是独立的"""
        # Arrange & Act
        logger1 = setup_logger("test_debug", level=logging.DEBUG, log_to_file=False)
        logger2 = setup_logger("test_info", level=logging.INFO, log_to_file=False)

        # Assert - 它们是不同的类
        assert logger1 is not logger2

    def test_setup_logger_with_rotation(self):
        """测试：应配置日志轮转"""
        # Arrange & Act
        logger = setup_logger(
            "test_rotation",
            log_to_file=False,  # 不创建文件，只验证不报错
            max_bytes=1024,
            backup_count=3,
        )

        # Assert - logger 应创建成功
        assert logger is not None
        assert logger._name == "test_rotation"


class TestGetLogger:
    """测试获取 logger 实例"""

    def test_get_logger_returns_same_instance(self):
        """测试：相同名称应返回相同实例"""
        # Arrange & Act
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        # Assert
        assert logger1 is logger2

    def test_get_logger_different_names_different_instances(self):
        """测试：不同名称应返回不同实例"""
        # Arrange & Act
        logger1 = get_logger("logger_one")
        logger2 = get_logger("logger_two")

        # Assert
        assert logger1 is not logger2
        assert logger1._name == "logger_one"
        assert logger2._name == "logger_two"

    def test_get_logger_creates_if_not_exists(self):
        """测试：不存在的 logger 应自动创建"""
        # Arrange & Act
        logger = get_logger("new_logger")

        # Assert
        assert logger is not None
        assert logger._name == "new_logger"


class TestLogOutput:
    """测试日志输出"""

    def test_log_message_in_file(self, tmp_path):
        """测试：日志消息应写入文件"""
        # Arrange
        logger = setup_logger(
            "test_output",
            log_to_file=True,
            log_dir=tmp_path,
            log_file="output.log",
            use_timestamp=False,
        )
        log_file = tmp_path / "output.log"

        # Act
        logger.info("测试输出消息")

        # 等待异步写入完成
        import time

        time.sleep(0.2)

        # Assert
        content = log_file.read_text()
        assert "测试输出消息" in content

    def test_log_levels_in_file(self, tmp_path):
        """测试：不同级别日志应正确记录"""
        # Arrange
        logger = setup_logger(
            "test_levels",
            log_to_file=True,
            log_dir=tmp_path,
            log_file="levels.log",
            level=logging.DEBUG,
            use_timestamp=False,
        )
        log_file = tmp_path / "levels.log"

        # Act
        logger.debug("调试消息")
        logger.info("信息消息")
        logger.warning("警告消息")
        logger.error("错误消息")

        # 等待日志文件写入完成（loguru 使用异步写入）
        import time

        time.sleep(0.2)

        # Assert - 检查日志文件包含所有消息
        content = log_file.read_text()
        # 由于 loguru 格式，检查关键词（分别检查）
        assert "DEBUG" in content
        assert "调试消息" in content
        assert "INFO" in content
        assert "信息消息" in content
        assert "WARNING" in content
        assert "警告消息" in content
        assert "ERROR" in content
        assert "错误消息" in content

    def test_log_rotation_creates_file(self, tmp_path):
        """测试：日志轮转应创建文件"""
        # Arrange
        logger = setup_logger(
            "test_rotate",
            log_to_file=True,
            log_dir=tmp_path,
            log_file="rotate.log",
            max_bytes=100,  # 很小，触发轮转
            backup_count=2,
            use_timestamp=False,
        )
        log_file = tmp_path / "rotate.log"

        # Act - 写入数据
        logger.info("测试消息")

        # Assert - 日志文件应该存在
        assert log_file.exists()
