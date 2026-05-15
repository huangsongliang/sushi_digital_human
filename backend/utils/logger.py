"""
日志工具模块
基于 Loguru 封装的结构化日志工具，支持：
- 控制台输出（带颜色）
- 文件日志（自动轮转）
- 结构化日志格式
- 上下文追踪
"""

from loguru import logger
import sys
from pathlib import Path
from typing import Optional

# 日志目录配置
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = "app.log",
    rotation: str = "500 MB",
    retention: str = "7 days",
    format_string: Optional[str] = None
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）
        log_file: 日志文件名，None 则只输出到控制台
        rotation: 日志轮转大小
        retention: 日志保留时间
        format_string: 自定义格式字符串
    """
    # 移除默认的 logger 配置
    logger.remove()

    # 设置日志格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # 控制台输出配置
    logger.add(
        sys.stdout,
        level=level,
        format=format_string,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # 文件输出配置
    if log_file:
        log_path = LOG_DIR / log_file
        logger.add(
            log_path,
            level=level,
            format=format_string,
            rotation=rotation,
            retention=retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )


def get_logger(name: Optional[str] = None) -> logger:
    """
    获取日志记录器实例

    Args:
        name: 模块名称，用于区分不同模块的日志

    Returns:
        Loguru logger 实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 初始化默认日志配置
setup_logger()

# 导出便捷方法
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
