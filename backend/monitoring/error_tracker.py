"""错误追踪模块

提供完整的错误追踪能力：
- 异常捕获和记录
- 错误聚合分析
- 错误堆栈管理
"""

import traceback
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ErrorInfo:
    """错误信息"""

    error_id: str
    error_type: str
    message: str
    traceback_str: str
    timestamp: datetime
    component: str
    method: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "traceback_str": self.traceback_str,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "method": self.method,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "context": self.context,
            "stack_trace": self.stack_trace,
        }


@dataclass
class ErrorAggregation:
    """错误聚合信息"""

    error_type: str
    component: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    sample_error: ErrorInfo
    frequency_per_hour: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_type": self.error_type,
            "component": self.component,
            "count": self.count,
            "first_occurrence": self.first_occurrence.isoformat(),
            "last_occurrence": self.last_occurrence.isoformat(),
            "sample_error": self.sample_error.to_dict(),
            "frequency_per_hour": self.frequency_per_hour,
        }


class ErrorTracker:
    """错误追踪器"""

    def __init__(self):
        """初始化错误追踪器"""
        self._errors: List[ErrorInfo] = []
        self._error_aggregations: Dict[str, ErrorAggregation] = {}
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._max_error_history = 5000

    def track_error(
        self,
        error: Exception,
        component: str,
        method: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorInfo:
        """追踪错误

        Args:
            error: 异常对象
            component: 组件名称
            method: 方法名称
            user_id: 用户ID
            request_id: 请求ID
            context: 上下文信息

        Returns:
            错误信息对象
        """
        error_id = str(uuid.uuid4())
        timestamp = datetime.now()
        error_type = type(error).__name__
        message = str(error)

        tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        stack_trace = self._parse_traceback(error.__traceback__)

        error_info = ErrorInfo(
            error_id=error_id,
            error_type=error_type,
            message=message,
            traceback_str=tb_str,
            timestamp=timestamp,
            component=component,
            method=method,
            user_id=user_id,
            request_id=request_id,
            context=context or {},
            stack_trace=stack_trace,
        )

        self._errors.append(error_info)
        self._error_counts[f"{error_type}:{component}"] += 1
        self._update_aggregation(error_info)
        self._cleanup_old_errors()

        logger.error(f"错误追踪 [{error_id}]: {error_type} in {component}.{method} - {message}")

        return error_info

    def track_error_manual(
        self,
        error_type: str,
        message: str,
        component: str,
        method: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        traceback_str: Optional[str] = None,
    ) -> ErrorInfo:
        """手动追踪错误（不使用异常对象）

        Args:
            error_type: 错误类型
            message: 错误消息
            component: 组件名称
            method: 方法名称
            user_id: 用户ID
            request_id: 请求ID
            context: 上下文信息
            traceback_str: 堆栈跟踪字符串

        Returns:
            错误信息对象
        """
        error_id = str(uuid.uuid4())
        timestamp = datetime.now()

        error_info = ErrorInfo(
            error_id=error_id,
            error_type=error_type,
            message=message,
            traceback_str=traceback_str or "",
            timestamp=timestamp,
            component=component,
            method=method,
            user_id=user_id,
            request_id=request_id,
            context=context or {},
            stack_trace=None,
        )

        self._errors.append(error_info)
        self._error_counts[f"{error_type}:{component}"] += 1
        self._update_aggregation(error_info)
        self._cleanup_old_errors()

        logger.error(f"错误追踪 [{error_id}]: {error_type} in {component}.{method} - {message}")

        return error_info

    def _parse_traceback(self, tb: Any) -> List[Dict[str, Any]]:
        """解析堆栈跟踪

        Args:
            tb: 堆栈跟踪对象

        Returns:
            解析后的堆栈跟踪列表
        """
        stack_trace = []
        while tb:
            stack_trace.append(
                {
                    "filename": tb.tb_frame.f_code.co_filename,
                    "lineno": tb.tb_lineno,
                    "function": tb.tb_frame.f_code.co_name,
                }
            )
            tb = tb.tb_next
        return stack_trace

    def _update_aggregation(self, error_info: ErrorInfo):
        """更新错误聚合信息

        Args:
            error_info: 错误信息对象
        """
        key = f"{error_info.error_type}:{error_info.component}"

        if key in self._error_aggregations:
            agg = self._error_aggregations[key]
            agg.count += 1
            agg.last_occurrence = error_info.timestamp
            if error_info.timestamp < agg.first_occurrence:
                agg.first_occurrence = error_info.timestamp

            hours = (agg.last_occurrence - agg.first_occurrence).total_seconds() / 3600
            agg.frequency_per_hour = agg.count / hours if hours > 0 else agg.count
        else:
            self._error_aggregations[key] = ErrorAggregation(
                error_type=error_info.error_type,
                component=error_info.component,
                count=1,
                first_occurrence=error_info.timestamp,
                last_occurrence=error_info.timestamp,
                sample_error=error_info,
                frequency_per_hour=0,
            )

    def get_error(self, error_id: str) -> Optional[ErrorInfo]:
        """获取错误详情

        Args:
            error_id: 错误ID

        Returns:
            错误信息对象
        """
        for error in reversed(self._errors):
            if error.error_id == error_id:
                return error
        return None

    def get_errors(
        self,
        component: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """获取错误列表

        Args:
            component: 组件名称过滤
            error_type: 错误类型过滤
            limit: 返回数量限制
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            错误列表
        """
        errors = self._errors

        if component:
            errors = [e for e in errors if e.component == component]
        if error_type:
            errors = [e for e in errors if e.error_type == error_type]
        if start_time:
            errors = [e for e in errors if e.timestamp >= start_time]
        if end_time:
            errors = [e for e in errors if e.timestamp <= end_time]

        errors.sort(key=lambda x: x.timestamp, reverse=True)
        return [e.to_dict() for e in errors[:limit]]

    def get_aggregated_errors(
        self, min_count: int = 1, sort_by: str = "count"
    ) -> List[Dict[str, Any]]:
        """获取聚合后的错误信息

        Args:
            min_count: 最小错误数量
            sort_by: 排序字段（count, frequency, last_occurrence）

        Returns:
            聚合错误列表
        """
        aggregations = [agg for agg in self._error_aggregations.values() if agg.count >= min_count]

        if sort_by == "count":
            aggregations.sort(key=lambda x: x.count, reverse=True)
        elif sort_by == "frequency":
            aggregations.sort(key=lambda x: x.frequency_per_hour, reverse=True)
        elif sort_by == "last_occurrence":
            aggregations.sort(key=lambda x: x.last_occurrence, reverse=True)

        return [agg.to_dict() for agg in aggregations]

    def get_error_statistics(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """获取错误统计信息

        Args:
            time_window: 时间窗口（分钟）

        Returns:
            错误统计信息
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=time_window) if time_window else None

        recent_errors = self._errors if not cutoff_time else [e for e in self._errors if e.timestamp >= cutoff_time]

        if not recent_errors:
            return {
                "total_errors": 0,
                "error_types": 0,
                "affected_components": 0,
                "avg_errors_per_hour": 0,
            }

        error_types = set(e.error_type for e in recent_errors)
        components = set(e.component for e in recent_errors)

        time_span_hours = 1 if not time_window else time_window / 60
        if time_span_hours == 0:
            time_span_hours = 1

        return {
            "total_errors": len(recent_errors),
            "error_types": len(error_types),
            "affected_components": len(components),
            "avg_errors_per_hour": len(recent_errors) / time_span_hours,
            "time_window_minutes": time_window,
        }

    def get_component_errors(self, component: str) -> Dict[str, Any]:
        """获取组件的错误统计

        Args:
            component: 组件名称

        Returns:
            组件错误统计
        """
        component_errors = [e for e in self._errors if e.component == component]
        error_types = defaultdict(int)

        for error in component_errors:
            error_types[error.error_type] += 1

        return {
            "component": component,
            "total_errors": len(component_errors),
            "error_types_breakdown": dict(error_types),
            "recent_errors": [e.to_dict() for e in component_errors[-10:]],
        }

    def get_stack_trace(self, error_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取错误堆栈跟踪

        Args:
            error_id: 错误ID

        Returns:
            堆栈跟踪列表
        """
        error = self.get_error(error_id)
        if error:
            return error.stack_trace
        return None

    def analyze_errors(self) -> List[Dict[str, Any]]:
        """分析错误模式

        Returns:
            错误分析结果列表
        """
        analysis = []

        for error_type, count in self._error_counts.items():
            error_type_name, component = error_type.split(":", 1)

            if count >= 10:
                analysis.append(
                    {
                        "issue": "frequent_error",
                        "severity": "critical" if count >= 50 else "warning",
                        "error_type": error_type_name,
                        "component": component,
                        "count": count,
                        "recommendation": f"该错误已发生{count}次，需要立即调查",
                    }
                )

        recent_time = datetime.now() - timedelta(hours=1)
        recent_errors = [e for e in self._errors if e.timestamp >= recent_time]

        if len(recent_errors) > 100:
            analysis.append(
                {
                    "issue": "high_error_rate",
                    "severity": "critical",
                    "error_count": len(recent_errors),
                    "recommendation": "过去1小时内发生了大量错误，系统可能存在严重问题",
                }
            )

        return analysis

    def _cleanup_old_errors(self):
        """清理旧的错误记录"""
        if len(self._errors) > self._max_error_history:
            self._errors = self._errors[-self._max_error_history :]


def error_tracker_context(
    component: str,
    method: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
):
    """错误追踪上下文管理器装饰器

    Args:
        component: 组件名称
        method: 方法名称
        user_id: 用户ID
        request_id: 请求ID

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            tracker = get_error_tracker()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tracker.track_error(
                    error=e,
                    component=component,
                    method=method or func.__name__,
                    user_id=user_id,
                    request_id=request_id,
                    context={"args": str(args), "kwargs": str(kwargs)},
                )
                raise

        return wrapper

    return decorator


def get_error_tracker() -> ErrorTracker:
    """获取错误追踪器单例

    Returns:
        错误追踪器实例
    """
    if not hasattr(get_error_tracker, "_instance"):
        get_error_tracker._instance = ErrorTracker()
    return get_error_tracker._instance
