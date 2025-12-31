"""
日志模块 - 基于 loguru 的日志配置

提供统一的日志配置和管理：
- 控制台输出（带颜色）
- 文件输出（支持轮转）
- 可配置的日志级别
"""

import logging
from pathlib import Path
from typing import Literal

from loguru import logger as _logger

# 默认配置
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = "mind.log"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5

# 已创建的 logger 集合
_loggers: dict[str, type] = {}


def setup_logger(
    name: str,
    *,
    level: int | str = DEFAULT_LOG_LEVEL,
    log_to_file: bool = True,
    log_dir: Path | str = DEFAULT_LOG_DIR,
    log_file: str = DEFAULT_LOG_FILE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    format_string: str | None = None,
) -> type:
    """配置并返回一个 logger 类型

    Args:
        name: logger 名称
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_to_file: 是否记录到文件
        log_dir: 日志目录
        log_file: 日志文件名
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        format_string: 自定义日志格式

    Returns:
        logger 类型

    Examples:
        >>> logger = setup_logger("my_app")
        >>> logger.info("应用启动")
    """
    # 转换级别
    if isinstance(level, str):
        level = getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)

    # 默认格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 移除默认处理器
    _logger.remove()

    # 添加控制台处理器
    _logger.add(
        sink=lambda msg: print(msg, end=""),
        format=format_string,
        level=level,
        colorize=True,
    )

    # 添加文件处理器
    if log_to_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 使用 rotation 参数指定大小
        _logger.add(
            sink=log_path / log_file,
            format=format_string,
            level=level,
            rotation=max_bytes,
            retention=backup_count,
            enqueue=True,  # 异步写入，不阻塞主线程
            encoding="utf-8",
        )

    # 缓存 logger
    class _Logger:
        """Logger 包装类，提供静态方法"""

        _name = name

        @staticmethod
        def debug(msg: str, *args, **kwargs):
            """记录 DEBUG 级别日志"""
            _logger.opt(depth=1).debug(msg, *args, **kwargs)

        @staticmethod
        def info(msg: str, *args, **kwargs):
            """记录 INFO 级别日志"""
            _logger.opt(depth=1).info(msg, *args, **kwargs)

        @staticmethod
        def warning(msg: str, *args, **kwargs):
            """记录 WARNING 级别日志"""
            _logger.opt(depth=1).warning(msg, *args, **kwargs)

        @staticmethod
        def error(msg: str, *args, **kwargs):
            """记录 ERROR 级别日志"""
            _logger.opt(depth=1).error(msg, *args, **kwargs)

        @staticmethod
        def critical(msg: str, *args, **kwargs):
            """记录 CRITICAL 级别日志"""
            _logger.opt(depth=1).critical(msg, *args, **kwargs)

        @staticmethod
        def exception(msg: str, *args, **kwargs):
            """记录异常信息（包含堆栈）"""
            _logger.opt(depth=1, exception=True).error(msg, *args, **kwargs)

    # 记录已创建的 logger
    _loggers[name] = _Logger

    return _Logger


def get_logger(name: str) -> type:
    """获取或创建指定名称的 logger

    Args:
        name: logger 名称

    Returns:
        logger 类型

    Examples:
        >>> logger = get_logger("my_app")
        >>> logger.info("消息")
    """
    if name in _loggers:
        return _loggers[name]

    # 使用默认配置创建
    return setup_logger(name)


def get_default_logger() -> type:
    """获取默认的 mind logger

    Returns:
        logger 类型
    """
    return get_logger("mind")
