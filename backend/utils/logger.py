"""
日志工具模块
基于 Loguru 封装的结构化日志工具，支持：
- 控制台输出（带颜色）
- 文件日志（自动轮转）
- 结构化日志格式（JSON）
- 请求追踪 ID
- 上下文日志
- Windows 终端 emoji 兼容
- 日志级别动态调整
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4
from contextvars import ContextVar
from contextlib import contextmanager

from loguru import logger
from typing import Any, Callable, Optional, Type

# 日志目录配置
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 检测操作系统
IS_WINDOWS = sys.platform.startswith("win")

# 请求追踪上下文变量
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="")
SESSION_ID: ContextVar[str] = ContextVar("session_id", default="")

def is_emoji(char: str) -> bool:
    """
    检测字符是否为 emoji
    
    Args:
        char: 单个字符
        
    Returns:
        True 如果是 emoji，False 否则
    """
    # emoji Unicode 范围
    # 参考: https://unicode.org/emoji/charts/full-emoji-list.html
    code = ord(char)
    
    # 基本 emoji 范围
    emoji_ranges = [
        (0x1F000, 0x1F0FF),  # 麻将牌
        (0x1F100, 0x1F1FF),  # 旗帜
        (0x1F200, 0x1F2FF),  # 方块
        (0x1F300, 0x1F5FF),  # 各种 emoji
        (0x1F600, 0x1F64F),  # 表情
        (0x1F680, 0x1F6FF),  # 交通和地图
        (0x1F700, 0x1F77F),  # 符号
        (0x1F780, 0x1F7FF),  # 几何形状
        (0x1F800, 0x1F8FF),  # 补充箭头
        (0x1F900, 0x1F9FF),  # 补充表情
        (0x1FA00, 0x1FAFF),  # 手势和符号
        (0x2600, 0x26FF),    # 杂项符号
        (0x2700, 0x27BF),    # 装饰符号
        (0x231A, 0x231B),    # 时钟
        (0x23E9, 0x23F3),    # 控制符
        (0x25FD, 0x25FE),    # 几何形状
        (0x2B05, 0x2B07),    # 箭头
        (0x2B1B, 0x2B1C),    # 方块
        (0x2B50, 0x2B50),    # 星号
        (0x2702, 0x2702),    # 剪刀
        (0x2705, 0x2705),    # 勾选
        (0x2708, 0x270D),    # 飞机、笔
        (0x2712, 0x2712),    # 十字
        (0x2714, 0x2714),    # 勾选
        (0x2716, 0x2716),    # 叉号
        (0x2728, 0x2728),    # 星星
        (0x274C, 0x274C),    # 红色叉号
        (0x274E, 0x274E),    # 雪花
        (0x2753, 0x2755),    # 问号
        (0x2757, 0x2757),    # 感叹号
        (0x2795, 0x2797),    # 加号、减号、乘号
        (0x2B1B, 0x2B1C),    # 黑白方块
        (0x3030, 0x3030),    # 波浪号
        (0x303D, 0x303D),    # 竖线
        (0xFE0E, 0xFE0F),    # 变体选择器
    ]
    
    for start, end in emoji_ranges:
        if start <= code <= end:
            return True
    return False


def remove_emoji(text: str) -> str:
    """
    移除文本中的 emoji 字符（用于 Windows 终端兼容）
    
    Args:
        text: 原始文本
        
    Returns:
        移除 emoji 后的文本
    """
    if not IS_WINDOWS:
        return text
    
    # 移除所有 emoji 字符
    return ''.join(c for c in text if not is_emoji(c))


def emoji_safe_sink(message):
    """
    安全输出日志消息的 sink，自动处理 Windows 终端的 emoji 编码问题
    
    Args:
        message: Loguru 消息对象
    """
    # 获取格式化后的消息
    formatted = message.record["extra"].get("message") or str(message)
    
    # Windows 系统移除 emoji
    if IS_WINDOWS:
        formatted = remove_emoji(formatted)
    
    # 写入 stdout
    print(formatted, flush=True)


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

    # 控制台输出配置（Windows 使用 emoji 安全的 sink）
    if IS_WINDOWS:
        logger.add(
            lambda msg: print(remove_emoji(msg)),
            level=level,
            format=format_string,
            colorize=False,
            backtrace=True,
            diagnose=True
        )
    else:
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


def get_logger(name: Optional[str] = None) -> Any:
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

# ==================== 请求追踪功能 ====================

def set_request_id(request_id: Optional[str] = None) -> str:
    """
    设置请求追踪 ID
    
    Args:
        request_id: 请求 ID，如果为 None 则自动生成
        
    Returns:
        设置的请求 ID
    """
    if request_id is None:
        request_id = str(uuid4())
    REQUEST_ID.set(request_id)
    return request_id


def get_request_id() -> str:
    """
    获取当前请求 ID
    
    Returns:
        当前请求 ID
    """
    return REQUEST_ID.get()


def set_session_id(session_id: str) -> None:
    """
    设置会话 ID
    
    Args:
        session_id: 会话 ID
    """
    SESSION_ID.set(session_id)


def get_session_id() -> str:
    """
    获取当前会话 ID
    
    Returns:
        当前会话 ID
    """
    return SESSION_ID.get()


@contextmanager
def with_request_context(request_id: Optional[str] = None, session_id: Optional[str] = None):
    """
    上下文管理器：设置请求上下文
    
    Args:
        request_id: 请求 ID
        session_id: 会话 ID
    """
    token1 = REQUEST_ID.set(request_id or str(uuid4()))
    token2 = SESSION_ID.set(session_id or "")
    
    try:
        yield
    finally:
        REQUEST_ID.reset(token1)
        SESSION_ID.reset(token2)


# ==================== 结构化日志格式 ====================

def json_formatter(record: Dict[str, Any]) -> str:
    """
    JSON 结构化日志格式器
    
    Args:
        record: Loguru 记录对象
        
    Returns:
        JSON 格式的日志字符串
    """
    log_entry = {
        "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "level": record["level"].name,
        "level_no": record["level"].no,
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
        "request_id": REQUEST_ID.get(),
        "session_id": SESSION_ID.get(),
    }
    
    # 添加异常信息（如果有）
    if record.get("exception"):
        log_entry["exception"] = str(record["exception"])
    
    # 添加额外字段
    if record.get("extra"):
        for key, value in record["extra"].items():
            if key not in log_entry:
                log_entry[key] = value
    
    return json.dumps(log_entry, ensure_ascii=False)


def console_formatter(record: Dict[str, Any]) -> str:
    """
    控制台日志格式器（带颜色和请求追踪）
    
    Args:
        record: Loguru 记录对象
        
    Returns:
        格式化的日志字符串
    """
    request_id = REQUEST_ID.get()
    session_id = SESSION_ID.get()
    
    parts = []
    
    # 时间
    parts.append(f"<green>{record['time'].strftime('%Y-%m-%d %H:%M:%S')}</green>")
    
    # 级别
    parts.append(f"<level>{record['level'].name: <8}</level>")
    
    # 请求 ID（如果有）
    if request_id:
        parts.append(f"<magenta>[{request_id[:8]}]</magenta>")
    
    # 模块和行号
    parts.append(f"<cyan>{record['name']}:{record['function']}:{record['line']}</cyan>")
    
    # 消息
    parts.append(f"<level>{record['message']}</level>")
    
    return " | ".join(parts) + "\n"


# ==================== 日志包装器 ====================

class StructuredLogger:
    """
    结构化日志包装器，提供统一的日志接口
    """
    
    def __init__(self, name: Optional[str] = None):
        self._logger = logger.bind(name=name) if name else logger
    
    def debug(self, message: str, **kwargs):
        """调试级别日志"""
        self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息级别日志"""
        self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告级别日志"""
        self._logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误级别日志"""
        self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误级别日志"""
        self._logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """异常日志（自动添加堆栈信息）"""
        self._logger.exception(message, **kwargs)
    
    def log_with_context(self, level: str, message: str, **context):
        """
        带上下文信息的日志记录
        
        Args:
            level: 日志级别
            message: 日志消息
            **context: 额外的上下文信息
        """
        extra = {"request_id": get_request_id(), "session_id": get_session_id()}
        extra.update(context)
        self._logger.log(level, message, **extra)


# ==================== 性能日志装饰器 ====================

def log_function_call(logger_instance=None):
    """
    装饰器：记录函数调用和执行时间
    
    Args:
        logger_instance: 自定义日志实例
    """
    def decorator(func):
        import asyncio
        import time
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                log = logger_instance or logger
                log.debug(f"调用函数: {func.__name__}")
                
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    log.debug(f"函数 {func.__name__} 执行完成，耗时: {duration:.4f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    log.error(f"函数 {func.__name__} 执行失败，耗时: {duration:.4f}s，错误: {str(e)}")
                    raise
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                log = logger_instance or logger
                log.debug(f"调用函数: {func.__name__}")
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    log.debug(f"函数 {func.__name__} 执行完成，耗时: {duration:.4f}s")
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    log.error(f"函数 {func.__name__} 执行失败，耗时: {duration:.4f}s，错误: {str(e)}")
                    raise
            
            return sync_wrapper
    
    return decorator


# ==================== 导出便捷方法 ====================

debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical
exception = logger.exception
