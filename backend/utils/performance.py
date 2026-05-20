"""性能监控模块
支持 Prometheus 指标暴露和自定义指标注册
"""

import time
import asyncio
from typing import Dict, List, Any, Callable
from contextlib import contextmanager

from backend.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Summary,
        generate_latest,
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not installed, metrics will not be exposed")

_registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

REQUEST_COUNTER = (
    Counter(
        "sushi_requests_total",
        "Total number of requests",
        ["endpoint", "method", "status"],
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)

REQUEST_DURATION = (
    Histogram(
        "sushi_request_duration_seconds",
        "Request duration in seconds",
        ["endpoint", "method"],
        registry=_registry,
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    )
    if PROMETHEUS_AVAILABLE
    else None
)

LLM_CALL_COUNTER = (
    Counter(
        "sushi_llm_calls_total",
        "Total number of LLM calls",
        ["model", "success"],
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)

LLM_TOKEN_USAGE = (
    Summary(
        "sushi_llm_token_usage",
        "LLM token usage",
        ["model", "type"],
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)

RETRIEVAL_DURATION = (
    Histogram(
        "sushi_retrieval_duration_seconds",
        "Retrieval duration in seconds",
        ["method"],
        registry=_registry,
        buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
    )
    if PROMETHEUS_AVAILABLE
    else None
)

RETRIEVAL_DOCUMENTS = (
    Summary(
        "sushi_retrieval_documents_found",
        "Number of documents found in retrieval",
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)

MEMORY_OPS_COUNTER = (
    Counter(
        "sushi_memory_operations_total",
        "Total number of memory operations",
        ["operation", "success"],
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)

APP_UPTIME = (
    Gauge("sushi_uptime_seconds", "Application uptime in seconds", registry=_registry)
    if PROMETHEUS_AVAILABLE
    else None
)

ACTIVE_SESSIONS = (
    Gauge("sushi_active_sessions", "Number of active sessions", registry=_registry)
    if PROMETHEUS_AVAILABLE
    else None
)

ERROR_COUNTER = (
    Counter(
        "sushi_errors_total",
        "Total number of errors",
        ["type", "endpoint"],
        registry=_registry,
    )
    if PROMETHEUS_AVAILABLE
    else None
)


class Timer:
    """计时器工具"""

    def __init__(self, name: str = "timer"):
        self.name = name
        self.start_time = None
        self.elapsed = 0.0

    def start(self):
        """开始计时"""
        self.start_time = time.perf_counter()

    def stop(self) -> float:
        """停止计时并返回耗时"""
        if self.start_time is not None:
            self.elapsed = time.perf_counter() - self.start_time
            return self.elapsed
        return 0.0

    def reset(self):
        """重置计时器"""
        self.start_time = None
        self.elapsed = 0.0

    @contextmanager
    def measure(self):
        """上下文管理器模式"""
        self.start()
        try:
            yield self
        finally:
            self.stop()


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self._metrics: Dict[str, List[float]] = {}
        self._request_count = 0
        self._total_time = 0.0
        self._start_time = time.time()

    def record(self, operation: str, duration: float):
        """记录操作耗时"""
        if operation not in self._metrics:
            self._metrics[operation] = []
        self._metrics[operation].append(duration)

    def increment_request_count(self):
        """增加请求计数"""
        self._request_count += 1

    def add_request_time(self, duration: float):
        """添加请求耗时"""
        self._total_time += duration

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = {}
        for operation, durations in self._metrics.items():
            if durations:
                metrics[operation] = {
                    "count": len(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "p95": self._calculate_percentile(durations, 95),
                    "p99": self._calculate_percentile(durations, 99),
                }

        uptime = time.time() - self._start_time

        return {
            "uptime": uptime,
            "request_count": self._request_count,
            "avg_request_time": (self._total_time / max(self._request_count, 1)),
            "operations": metrics,
        }

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def reset(self):
        """重置所有指标"""
        self._metrics = {}
        self._request_count = 0
        self._total_time = 0.0
        self._start_time = time.time()


performance_monitor = PerformanceMonitor()


@contextmanager
def timed_operation(operation_name: str):
    """带监控的计时上下文管理器"""
    timer = Timer(operation_name)
    timer.start()
    try:
        yield timer
    finally:
        elapsed = timer.stop()
        performance_monitor.record(operation_name, elapsed)
        logger.debug(f"[{operation_name}] 耗时: {elapsed:.4f}s")


async def async_timed_operation(operation_name: str):
    """异步版本的带监控计时"""
    timer = Timer(operation_name)
    timer.start()

    class AsyncTimerContext:
        def __init__(self, timer_ref):
            self.timer = timer_ref

        async def __aenter__(self):
            return self.timer

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            elapsed = self.timer.stop()
            performance_monitor.record(operation_name, elapsed)
            logger.debug(f"[{operation_name}] 耗时: {elapsed:.4f}s")

    return AsyncTimerContext(timer)


def log_performance_summary():
    """记录性能摘要日志"""
    metrics = performance_monitor.get_metrics()
    logger.info(
        f"性能摘要: 请求数={metrics['request_count']}, "
        f"平均耗时={metrics['avg_request_time']:.4f}s, "
        f"运行时间={metrics['uptime']:.2f}s"
    )


async def periodic_performance_log(interval: int = 60):
    """定期输出性能日志并记录告警指标"""
    while True:
        log_performance_summary()
        
        # 记录告警指标
        metrics = performance_monitor.get_metrics()
        try:
            from backend.utils.alerting import record_alert_metric
            
            # 记录平均延迟
            record_alert_metric("avg_latency", metrics.get("avg_request_time", 0.0))
            
            # 计算并记录错误率（基于请求计数）
            if ERROR_COUNTER is not None:
                error_count = ERROR_COUNTER._metrics.get("exception", {}).get("unknown", 0)
                total_requests = metrics.get("request_count", 1)
                error_rate = error_count / total_requests if total_requests > 0 else 0.0
                record_alert_metric("error_rate", error_rate)
            
            # 记录并发数估计
            record_alert_metric("concurrency", min(metrics.get("request_count", 0) // 10, 100))
            
        except ImportError:
            pass
        
        await asyncio.sleep(interval)


def generate_prometheus_metrics() -> bytes:
    """生成 Prometheus 格式的指标数据"""
    if not PROMETHEUS_AVAILABLE or _registry is None:
        return b"# Prometheus client not available\n"

    try:
        if APP_UPTIME is not None:
            APP_UPTIME.set(time.time() - performance_monitor._start_time)

        if ACTIVE_SESSIONS is not None:
            ACTIVE_SESSIONS.set(min(performance_monitor._request_count // 10, 100))

        return generate_latest(_registry)
    except Exception:
        logger.error("Failed to generate Prometheus metrics")
        return b"# Error generating metrics\n"


def get_prometheus_content_type() -> str:
    """获取 Prometheus 内容类型"""
    return CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else "text/plain"


def track_request(endpoint: str, method: str = "POST"):
    """装饰器：追踪请求"""

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                if ERROR_COUNTER is not None:
                    ERROR_COUNTER.labels(type="exception", endpoint=endpoint).inc()
                raise
            finally:
                duration = time.time() - start_time
                if REQUEST_COUNTER is not None:
                    REQUEST_COUNTER.labels(
                        endpoint=endpoint, method=method, status=status
                    ).inc()
                if REQUEST_DURATION is not None:
                    REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
                        duration
                    )

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                if ERROR_COUNTER is not None:
                    ERROR_COUNTER.labels(type="exception", endpoint=endpoint).inc()
                raise
            finally:
                duration = time.time() - start_time
                if REQUEST_COUNTER is not None:
                    REQUEST_COUNTER.labels(
                        endpoint=endpoint, method=method, status=status
                    ).inc()
                if REQUEST_DURATION is not None:
                    REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(
                        duration
                    )

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_llm_call(model: str):
    """装饰器：追踪 LLM 调用"""

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            success = "true"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = "false"
                raise
            finally:
                if LLM_CALL_COUNTER is not None:
                    LLM_CALL_COUNTER.labels(model=model, success=success).inc()

        def sync_wrapper(*args, **kwargs):
            success = "true"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = "false"
                raise
            finally:
                if LLM_CALL_COUNTER is not None:
                    LLM_CALL_COUNTER.labels(model=model, success=success).inc()

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_retrieval(method: str = "hybrid"):
    """装饰器：追踪检索操作"""

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                if RETRIEVAL_DOCUMENTS is not None:
                    doc_count = len(result) if isinstance(result, list) else 0
                    RETRIEVAL_DOCUMENTS.observe(doc_count)
                return result
            finally:
                duration = time.time() - start_time
                if RETRIEVAL_DURATION is not None:
                    RETRIEVAL_DURATION.labels(method=method).observe(duration)

        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                if RETRIEVAL_DOCUMENTS is not None:
                    doc_count = len(result) if isinstance(result, list) else 0
                    RETRIEVAL_DOCUMENTS.observe(doc_count)
                return result
            finally:
                duration = time.time() - start_time
                if RETRIEVAL_DURATION is not None:
                    RETRIEVAL_DURATION.labels(method=method).observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_memory_operation(operation: str):
    """装饰器：追踪内存操作"""

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            success = "true"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = "false"
                raise
            finally:
                if MEMORY_OPS_COUNTER is not None:
                    MEMORY_OPS_COUNTER.labels(
                        operation=operation, success=success
                    ).inc()

        def sync_wrapper(*args, **kwargs):
            success = "true"
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = "false"
                raise
            finally:
                if MEMORY_OPS_COUNTER is not None:
                    MEMORY_OPS_COUNTER.labels(
                        operation=operation, success=success
                    ).inc()

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def record_request(endpoint: str, method: str, status: str, duration: float):
    """记录请求指标"""
    if REQUEST_COUNTER is not None:
        REQUEST_COUNTER.labels(endpoint=endpoint, method=method, status=status).inc()
    if REQUEST_DURATION is not None:
        REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)


def record_llm_call(
    model: str, success: bool, prompt_tokens: int = 0, completion_tokens: int = 0
):
    """记录 LLM 调用指标"""
    if LLM_CALL_COUNTER is not None:
        LLM_CALL_COUNTER.labels(
            model=model, success="true" if success else "false"
        ).inc()
    if LLM_TOKEN_USAGE is not None and prompt_tokens > 0:
        LLM_TOKEN_USAGE.labels(model=model, type="prompt").observe(prompt_tokens)
    if LLM_TOKEN_USAGE is not None and completion_tokens > 0:
        LLM_TOKEN_USAGE.labels(model=model, type="completion").observe(
            completion_tokens
        )


def record_error(error_type: str, endpoint: str = "unknown"):
    """记录错误指标"""
    if ERROR_COUNTER is not None:
        ERROR_COUNTER.labels(type=error_type, endpoint=endpoint).inc()


def record_retrieval_result(method: str, duration: float, document_count: int):
    """记录检索结果指标"""
    if RETRIEVAL_DURATION is not None:
        RETRIEVAL_DURATION.labels(method=method).observe(duration)
    if RETRIEVAL_DOCUMENTS is not None:
        RETRIEVAL_DOCUMENTS.observe(document_count)


def record_memory_operation(operation: str, success: bool):
    """记录内存操作指标"""
    if MEMORY_OPS_COUNTER is not None:
        MEMORY_OPS_COUNTER.labels(
            operation=operation, success="true" if success else "false"
        ).inc()
