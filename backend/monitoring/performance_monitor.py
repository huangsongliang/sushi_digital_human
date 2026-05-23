"""性能监控模块

提供完整的性能监控能力：
- 性能指标收集
- 请求链路可视化数据
- 性能瓶颈分析
"""

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标"""

    metric_id: str
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class RequestMetrics:
    """请求性能指标"""

    request_id: str
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_size: Optional[int] = None
    response_size: Optional[int] = None
    cache_hit: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "request_id": self.request_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status_code": self.status_code,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_size": self.request_size,
            "response_size": self.response_size,
            "cache_hit": self.cache_hit,
            "error": self.error,
        }


@dataclass
class BottleneckAnalysis:
    """性能瓶颈分析结果"""

    component: str
    issue_type: str
    severity: str
    description: str
    metric_name: str
    current_value: float
    threshold: float
    recommendation: str
    detected_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "component": self.component,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "description": self.description,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "recommendation": self.recommendation,
            "detected_at": self.detected_at.isoformat(),
        }


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        """初始化性能监控器"""
        self._metrics: List[PerformanceMetric] = []
        self._request_metrics: Dict[str, RequestMetrics] = {}
        self._endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "total_duration": 0, "errors": 0, "durations": []}
        )
        self._bottlenecks: List[BottleneckAnalysis] = []
        self._max_metrics_history = 10000
        self._max_request_history = 5000
        self._thresholds = {
            "response_time_p95": 1000,
            "response_time_p99": 2000,
            "error_rate": 0.05,
            "cpu_usage": 80,
            "memory_usage": 85,
        }

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PerformanceMetric:
        """记录性能指标

        Args:
            name: 指标名称
            value: 指标值
            unit: 单位
            tags: 标签
            metadata: 元数据

        Returns:
            性能指标对象
        """
        metric = PerformanceMetric(
            metric_id=str(uuid.uuid4()),
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            tags=tags or {},
            metadata=metadata or {},
        )
        self._metrics.append(metric)
        self._cleanup_old_metrics()
        return metric

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        cache_hit: bool = False,
        error: Optional[str] = None,
    ) -> RequestMetrics:
        """记录请求性能指标

        Args:
            endpoint: 请求端点
            method: HTTP方法
            status_code: 状态码
            duration_ms: 持续时间（毫秒）
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            request_size: 请求大小
            response_size: 响应大小
            cache_hit: 是否缓存命中
            error: 错误信息

        Returns:
            请求性能指标对象
        """
        request_id = str(uuid.uuid4())
        request_metrics = RequestMetrics(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            request_size=request_size,
            response_size=response_size,
            cache_hit=cache_hit,
            error=error,
        )

        self._request_metrics[request_id] = request_metrics
        self._update_endpoint_stats(endpoint, duration_ms, status_code >= 400)
        self._check_performance_thresholds(endpoint, duration_ms, status_code)
        self._cleanup_old_requests()
        return request_metrics

    def _update_endpoint_stats(self, endpoint: str, duration_ms: float, is_error: bool):
        """更新端点统计信息

        Args:
            endpoint: 端点
            duration_ms: 持续时间
            is_error: 是否为错误
        """
        stats = self._endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_duration"] += duration_ms
        if is_error:
            stats["errors"] += 1
        stats["durations"].append(duration_ms)

        if len(stats["durations"]) > 1000:
            stats["durations"] = stats["durations"][-1000:]

    def _check_performance_thresholds(self, endpoint: str, duration_ms: float, status_code: int):
        """检查性能阈值

        Args:
            endpoint: 端点
            duration_ms: 持续时间
            status_code: 状态码
        """
        stats = self._endpoint_stats[endpoint]
        durations = stats["durations"]

        if len(durations) >= 100:
            p95 = sorted(durations)[int(len(durations) * 0.95)]
            p99 = sorted(durations)[int(len(durations) * 0.99)]
            error_rate = stats["errors"] / stats["count"]

            if duration_ms > self._thresholds["response_time_p95"]:
                self._add_bottleneck(
                    component=endpoint,
                    issue_type="high_latency",
                    severity="warning",
                    description=f"响应时间P95超过阈值: {p95:.2f}ms > {self._thresholds['response_time_p95']}ms",
                    metric_name="response_time_p95",
                    current_value=p95,
                    threshold=self._thresholds["response_time_p95"],
                    recommendation="考虑添加缓存、优化数据库查询或增加服务器资源",
                )

            if duration_ms > self._thresholds["response_time_p99"]:
                self._add_bottleneck(
                    component=endpoint,
                    issue_type="critical_latency",
                    severity="critical",
                    description=f"响应时间P99超过阈值: {p99:.2f}ms > {self._thresholds['response_time_p99']}ms",
                    metric_name="response_time_p99",
                    current_value=p99,
                    threshold=self._thresholds["response_time_p99"],
                    recommendation="需要立即优化，可能存在严重性能问题",
                )

            if error_rate > self._thresholds["error_rate"]:
                self._add_bottleneck(
                    component=endpoint,
                    issue_type="high_error_rate",
                    severity="warning",
                    description=f"错误率超过阈值: {error_rate:.2%} > {self._thresholds['error_rate']:.2%}",
                    metric_name="error_rate",
                    current_value=error_rate,
                    threshold=self._thresholds["error_rate"],
                    recommendation="检查系统日志，定位错误原因并修复",
                )

    def _add_bottleneck(
        self,
        component: str,
        issue_type: str,
        severity: str,
        description: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        recommendation: str,
    ):
        """添加性能瓶颈分析结果

        Args:
            component: 组件
            issue_type: 问题类型
            severity: 严重程度
            description: 描述
            metric_name: 指标名称
            current_value: 当前值
            threshold: 阈值
            recommendation: 建议
        """
        bottleneck = BottleneckAnalysis(
            component=component,
            issue_type=issue_type,
            severity=severity,
            description=description,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            recommendation=recommendation,
            detected_at=datetime.now(),
        )

        existing_key = f"{component}:{issue_type}"
        existing = [b for b in self._bottlenecks if f"{b.component}:{b.issue_type}" == existing_key]

        if not existing or (datetime.now() - existing[0].detected_at) > timedelta(minutes=30):
            self._bottlenecks.append(bottleneck)
            logger.warning(f"性能瓶颈检测: {description}")

    def get_endpoint_stats(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """获取端点统计信息

        Args:
            endpoint: 端点（可选）

        Returns:
            统计信息字典
        """
        if endpoint:
            stats = self._endpoint_stats.get(endpoint)
            if not stats:
                return {}

            durations = stats["durations"]
            if not durations:
                return {
                    "endpoint": endpoint,
                    "count": 0,
                    "avg_duration_ms": 0,
                    "p50_duration_ms": 0,
                    "p95_duration_ms": 0,
                    "p99_duration_ms": 0,
                    "error_rate": 0,
                }

            sorted_durations = sorted(durations)
            return {
                "endpoint": endpoint,
                "count": stats["count"],
                "avg_duration_ms": stats["total_duration"] / stats["count"],
                "p50_duration_ms": sorted_durations[len(sorted_durations) // 2],
                "p95_duration_ms": sorted_durations[int(len(sorted_durations) * 0.95)],
                "p99_duration_ms": sorted_durations[int(len(sorted_durations) * 0.99)],
                "error_rate": stats["errors"] / stats["count"],
            }

        return {endpoint: self.get_endpoint_stats(endpoint) for endpoint in self._endpoint_stats.keys()}

    def get_performance_summary(self, time_window: Optional[int] = None) -> Dict[str, Any]:
        """获取性能摘要

        Args:
            time_window: 时间窗口（分钟）

        Returns:
            性能摘要
        """
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=time_window) if time_window else None

        recent_metrics = self._metrics if not cutoff_time else [m for m in self._metrics if m.timestamp >= cutoff_time]
        recent_requests = (
            list(self._request_metrics.values())
            if not cutoff_time
            else [r for r in self._request_metrics.values() if r.timestamp >= cutoff_time]
        )

        if not recent_requests:
            return {
                "total_requests": 0,
                "avg_duration_ms": 0,
                "p95_duration_ms": 0,
                "p99_duration_ms": 0,
                "error_rate": 0,
                "cache_hit_rate": 0,
            }

        durations = [r.duration_ms for r in recent_requests]
        sorted_durations = sorted(durations)
        errors = [r for r in recent_requests if r.status_code >= 400]
        cache_hits = [r for r in recent_requests if r.cache_hit]

        return {
            "total_requests": len(recent_requests),
            "avg_duration_ms": sum(durations) / len(durations),
            "p50_duration_ms": sorted_durations[len(sorted_durations) // 2],
            "p95_duration_ms": sorted_durations[int(len(sorted_durations) * 0.95)],
            "p99_duration_ms": sorted_durations[int(len(sorted_durations) * 0.99)],
            "error_rate": len(errors) / len(recent_requests),
            "cache_hit_rate": len(cache_hits) / len(recent_requests) if recent_requests else 0,
            "time_window_minutes": time_window,
        }

    def get_bottlenecks(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取性能瓶颈列表

        Args:
            severity: 严重程度过滤

        Returns:
            瓶颈列表
        """
        bottlenecks = self._bottlenecks
        if severity:
            bottlenecks = [b for b in bottlenecks if b.severity == severity]
        return [b.to_dict() for b in bottlenecks[-50:]]

    def get_request_trace_data(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取请求链路可视化数据

        Args:
            request_id: 请求ID

        Returns:
            链路数据
        """
        request_metrics = self._request_metrics.get(request_id)
        if not request_metrics:
            return None

        return {
            "request": request_metrics.to_dict(),
            "phases": [
                {"phase": "total", "duration_ms": request_metrics.duration_ms},
            ],
            "context": {
                "user_id": request_metrics.user_id,
                "ip_address": request_metrics.ip_address,
                "user_agent": request_metrics.user_agent,
            },
        }

    def analyze_bottlenecks(self) -> List[Dict[str, Any]]:
        """执行性能瓶颈分析

        Returns:
            瓶颈分析结果列表
        """
        results = []

        for endpoint, stats in self._endpoint_stats.items():
            if stats["count"] == 0:
                continue

            avg_duration = stats["total_duration"] / stats["count"]
            error_rate = stats["errors"] / stats["count"]

            if avg_duration > self._thresholds["response_time_p95"]:
                results.append(
                    {
                        "component": endpoint,
                        "issue_type": "slow_response",
                        "severity": "warning",
                        "avg_duration_ms": avg_duration,
                        "threshold_ms": self._thresholds["response_time_p95"],
                        "recommendation": "优化该端点的处理逻辑",
                    }
                )

            if error_rate > self._thresholds["error_rate"]:
                results.append(
                    {
                        "component": endpoint,
                        "issue_type": "high_error_rate",
                        "severity": "critical" if error_rate > 0.1 else "warning",
                        "error_rate": error_rate,
                        "threshold": self._thresholds["error_rate"],
                        "recommendation": "检查并修复该端点的错误",
                    }
                )

        return results

    def _cleanup_old_metrics(self):
        """清理旧的指标数据"""
        if len(self._metrics) > self._max_metrics_history:
            self._metrics = self._metrics[-self._max_metrics_history :]

    def _cleanup_old_requests(self):
        """清理旧的请求数据"""
        if len(self._request_metrics) > self._max_request_history:
            sorted_requests = sorted(self._request_metrics.items(), key=lambda x: x[1].timestamp)
            to_remove = sorted_requests[: len(sorted_requests) - self._max_request_history]
            for request_id, _ in to_remove:
                del self._request_metrics[request_id]


class PerformanceTimer:
    """性能计时器上下文管理器"""

    def __init__(self, monitor: PerformanceMonitor, name: str, tags: Optional[Dict[str, str]] = None):
        """初始化性能计时器

        Args:
            monitor: 性能监控器
            name: 指标名称
            tags: 标签
        """
        self.monitor = monitor
        self.name = name
        self.tags = tags or {}
        self.start_time = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration_ms = (time.time() - self.start_time) * 1000
        self.monitor.record_metric(
            name=self.name,
            value=duration_ms,
            unit="ms",
            tags=self.tags,
            metadata={"success": exc_type is None},
        )


def get_performance_monitor() -> PerformanceMonitor:
    """获取性能监控器单例

    Returns:
        性能监控器实例
    """
    if not hasattr(get_performance_monitor, "_instance"):
        get_performance_monitor._instance = PerformanceMonitor()
    return get_performance_monitor._instance
