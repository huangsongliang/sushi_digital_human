"""
错误追踪模块
提供统一的错误处理和告警功能，支持：
- 全局异常捕获
- 错误分类和统计
- 告警通知（日志、Webhook）
- 错误追踪 ID
- 错误上报
"""

import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from backend.utils.logger import get_logger, set_request_id
from backend.utils.performance import record_error

logger = get_logger(__name__)


@dataclass
class ErrorInfo:
    """错误信息数据类"""

    error_id: str
    error_type: str
    message: str
    stack_trace: str
    request_id: str
    endpoint: str
    method: str
    timestamp: datetime
    additional_info: Dict[str, Any]


class ErrorTracker:
    """错误追踪器"""

    def __init__(self):
        self._error_counts: Dict[str, int] = {}
        self._last_error_time: Dict[str, float] = {}
        self._alert_threshold = 5
        self._alert_cooldown = 60

    def track_error(self, error_type: str, message: str, **kwargs) -> str:
        """
        追踪错误

        Args:
            error_type: 错误类型
            message: 错误消息
            **kwargs: 额外信息（request_id, endpoint, method 等）

        Returns:
            错误 ID
        """
        error_id = str(uuid4())
        request_id = kwargs.get("request_id", "")
        endpoint = kwargs.get("endpoint", "unknown")
        method = kwargs.get("method", "GET")

        stack_trace = traceback.format_exc() if kwargs.get("include_stack", True) else ""

        record_error(error_type, endpoint)

        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1
        self._last_error_time[error_type] = time.time()

        self._check_alert(error_type)

        logger.error(
            f"[错误追踪] ID={error_id[:8]} 类型={error_type} 消息={message}",
            extra={
                "error_id": error_id,
                "error_type": error_type,
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "stack_trace": stack_trace,
                "additional_info": kwargs,
            },
        )

        return error_id

    def _check_alert(self, error_type: str):
        """
        检查是否需要发送告警

        Args:
            error_type: 错误类型
        """
        count = self._error_counts.get(error_type, 0)
        last_time = self._last_error_time.get(error_type, 0)
        current_time = time.time()

        if count >= self._alert_threshold and (current_time - last_time) < 60:
            self._send_alert(error_type, count)
            self._error_counts[error_type] = 0

    def _send_alert(self, error_type: str, count: int):
        """
        发送告警通知

        Args:
            error_type: 错误类型
            count: 错误数量
        """
        alert_message = f"告警：错误类型 '{error_type}' 在最近一分钟内发生 {count} 次"
        logger.critical(alert_message)

    def get_error_stats(self) -> Dict[str, Any]:
        """
        获取错误统计信息

        Returns:
            错误统计字典
        """
        return {
            "error_counts": self._error_counts.copy(),
            "total_errors": sum(self._error_counts.values()),
            "error_types": list(self._error_counts.keys()),
        }

    def reset_stats(self):
        """重置错误统计"""
        self._error_counts.clear()
        self._last_error_time.clear()


# 全局错误追踪实例
error_tracker = ErrorTracker()


def capture_exception(error: Exception, **kwargs) -> str:
    """
    捕获并追踪异常

    Args:
        error: 异常对象
        **kwargs: 额外信息

    Returns:
        错误 ID
    """
    return error_tracker.track_error(
        error_type=type(error).__name__,
        message=str(error),
        include_stack=True,
        **kwargs,
    )


def capture_message(message: str, error_type: str = "CustomError", **kwargs) -> str:
    """
    捕获自定义错误消息

    Args:
        message: 错误消息
        error_type: 错误类型
        **kwargs: 额外信息

    Returns:
        错误 ID
    """
    return error_tracker.track_error(error_type=error_type, message=message, include_stack=False, **kwargs)


def error_handler_middleware(func: Callable) -> Callable:
    """
    装饰器：统一错误处理中间件

    Args:
        func: 被装饰的函数

    Returns:
        包装后的函数
    """
    import asyncio

    if asyncio.iscoroutinefunction(func):

        async def async_wrapper(*args, **kwargs):
            request_id = set_request_id()

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    e,
                    request_id=request_id,
                    endpoint=kwargs.get("endpoint", "unknown"),
                    method=kwargs.get("method", "GET"),
                )
                raise

        return async_wrapper
    else:

        def sync_wrapper(*args, **kwargs):
            request_id = set_request_id()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    e,
                    request_id=request_id,
                    endpoint=kwargs.get("endpoint", "unknown"),
                    method=kwargs.get("method", "GET"),
                )
                raise

        return sync_wrapper


def get_error_info(error_id: str) -> Optional[ErrorInfo]:
    """
    根据错误 ID 获取错误详情（预留接口，可扩展存储）

    Args:
        error_id: 错误 ID

    Returns:
        错误信息对象
    """
    return None


# ==================== FastAPI 异常处理器 ====================


def setup_exception_handlers(app):
    """
    为 FastAPI 应用设置全局异常处理器

    Args:
        app: FastAPI 应用实例
    """
    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        set_request_id(request_id)

        capture_exception(
            exc,
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "error_id": str(uuid4()),
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP 异常处理器"""
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        set_request_id(request_id)

        if exc.status_code >= 500:
            capture_exception(
                exc,
                request_id=request_id,
                endpoint=str(request.url.path),
                method=request.method,
            )

        if isinstance(exc.detail, dict):
            error_type = exc.detail.get("error", "HTTP_ERROR")
            message = exc.detail.get("message", str(exc.detail))
            detail = exc.detail.get("detail")
        else:
            error_type = "HTTP_ERROR"
            message = str(exc.detail)
            detail = None

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": error_type,
                "message": message,
                "detail": detail,
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
            },
        )
