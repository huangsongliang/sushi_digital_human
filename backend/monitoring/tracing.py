"""全链路追踪模块

提供完整的分布式追踪能力：
- OpenTelemetry 深度集成
- OTLP 导出器配置
- 自动仪表化装饰器
- Trace ID 和 Span 管理
"""

import functools
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import Span
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SpanInfo:
    """Span信息"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "OK"
    error_message: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_message": self.error_message,
            "tags": self.tags,
            "attributes": self.attributes,
            "events": self.events,
        }


class OTLPExporterConfig:
    """OTLP导出器配置"""

    def __init__(
        self,
        endpoint: str = "http://localhost:4317",
        insecure: bool = True,
        timeout: int = 30,
    ):
        """初始化OTLP导出器配置

        Args:
            endpoint: OTLP接收端点地址
            insecure: 是否使用不安全连接
            timeout: 超时时间（秒）
        """
        self.endpoint = endpoint
        self.insecure = insecure
        self.timeout = timeout


class TracingManager:
    """全链路追踪管理器"""

    def __init__(self, service_name: str = "sushi_digital_human"):
        """初始化追踪管理器

        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self._tracer = None
        self._spans: Dict[str, SpanInfo] = {}
        self._active_spans: Dict[str, Span] = {}
        self._config = None
        self._initialized = False

        if OPENTELEMETRY_AVAILABLE:
            self._initialize_tracer()

    def _initialize_tracer(self):
        """初始化OpenTelemetry追踪器"""
        try:
            Resource.create({"service.name": self.service_name})  # noqa: F841
            self._tracer = trace.get_tracer(self.service_name)
            self._initialized = True
            logger.info(f"追踪器初始化成功: {self.service_name}")
        except Exception as e:
            logger.error(f"追踪器初始化失败: {e}")

    def configure_otlp_exporter(self, config: OTLPExporterConfig):
        """配置OTLP导出器

        Args:
            config: OTLP导出器配置
        """
        if not OPENTELEMETRY_AVAILABLE:
            logger.warning("OpenTelemetry未安装，无法配置OTLP导出器")
            return

        self._config = config
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=config.endpoint,
                insecure=config.insecure,
                timeout=config.timeout,
            )
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            logger.info(f"OTLP导出器配置成功: {config.endpoint}")
        except Exception as e:
            logger.error(f"OTLP导出器配置失败: {e}")

    def enable_console_exporter(self):
        """启用控制台导出器（用于调试）"""
        if not OPENTELEMETRY_AVAILABLE:
            return

        try:
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            logger.info("控制台导出器已启用")
        except Exception as e:
            logger.error(f"控制台导出器启用失败: {e}")

    @contextmanager
    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """启动一个新的Span

        Args:
            operation_name: 操作名称
            parent_span_id: 父Span ID
            tags: 标签
            attributes: 属性

        Yields:
            SpanInfo: Span信息对象
        """
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]

        start_time = datetime.now()
        span_info = SpanInfo(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=start_time,
            tags=tags or {},
            attributes=attributes or {},
        )

        self._spans[span_id] = span_info
        self._active_spans[span_id] = span_info

        if OPENTELEMETRY_AVAILABLE and self._tracer:
            span = self._tracer.start_span(operation_name)
            self._active_spans[f"{trace_id}:{span_id}"] = span
            context = span.get_span_context()
            span_info.trace_id = format(context.trace_id, "032x")
            span_info.span_id = format(context.span_id, "016x")

        try:
            yield span_info
        except Exception as e:
            span_info.status = "ERROR"
            span_info.error_message = str(e)
            if self._active_spans.get(f"{trace_id}:{span_id}"):
                span = self._active_spans[f"{trace_id}:{span_id}"]
                if OPENTELEMETRY_AVAILABLE:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
            raise
        finally:
            span_info.end_time = datetime.now()
            span_info.duration_ms = (span_info.end_time - start_time).total_seconds() * 1000

            if OPENTELEMETRY_AVAILABLE and self._active_spans.get(f"{trace_id}:{span_id}"):
                span = self._active_spans[f"{trace_id}:{span_id}"]
                span.end()

            if f"{trace_id}:{span_id}" in self._active_spans:
                del self._active_spans[f"{trace_id}:{span_id}"]

    def trace_function(
        self,
        operation_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """追踪函数的装饰器

        Args:
            operation_name: 操作名称（默认为函数名）
            tags: 标签
            attributes: 属性

        Returns:
            装饰器函数
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or func.__name__
                with self.start_span(name, tags=tags, attributes=attributes) as span:
                    try:
                        result = func(*args, **kwargs)
                        return result
                    except Exception as e:
                        span.status = "ERROR"
                        span.error_message = str(e)
                        raise

            return wrapper

        return decorator

    def add_span_event(self, span_id: str, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """添加Span事件

        Args:
            span_id: Span ID
            event_name: 事件名称
            attributes: 事件属性
        """
        if span_id in self._spans:
            event = {
                "name": event_name,
                "timestamp": datetime.now().isoformat(),
                "attributes": attributes or {},
            }
            self._spans[span_id].events.append(event)

    def set_span_attribute(self, span_id: str, key: str, value: Any):
        """设置Span属性

        Args:
            span_id: Span ID
            key: 属性键
            value: 属性值
        """
        if span_id in self._spans:
            self._spans[span_id].attributes[key] = value

    def set_span_tag(self, span_id: str, key: str, value: str):
        """设置Span标签

        Args:
            span_id: Span ID
            key: 标签键
            value: 标签值
        """
        if span_id in self._spans:
            self._spans[span_id].tags[key] = value

    def get_span(self, span_id: str) -> Optional[SpanInfo]:
        """获取Span信息

        Args:
            span_id: Span ID

        Returns:
            Span信息对象
        """
        return self._spans.get(span_id)

    def get_trace(self, trace_id: str) -> List[SpanInfo]:
        """获取完整追踪的所有Span

        Args:
            trace_id: 追踪ID

        Returns:
            Span列表
        """
        return [span for span in self._spans.values() if span.trace_id == trace_id]

    def get_recent_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的追踪记录

        Args:
            limit: 返回数量限制

        Returns:
            追踪记录列表
        """
        unique_traces = {}
        for span in self._spans.values():
            if span.trace_id not in unique_traces:
                unique_traces[span.trace_id] = {
                    "trace_id": span.trace_id,
                    "operation_name": span.operation_name,
                    "start_time": span.start_time.isoformat(),
                    "end_time": span.end_time.isoformat() if span.end_time else None,
                    "duration_ms": span.duration_ms,
                    "status": span.status,
                    "span_count": 1,
                }
            else:
                unique_traces[span.trace_id]["span_count"] += 1

        traces = list(unique_traces.values())
        traces.sort(key=lambda x: x["start_time"], reverse=True)
        return traces[:limit]

    def inject_context(self, carrier: Dict[str, str]) -> Dict[str, str]:
        """注入追踪上下文到载体

        Args:
            carrier: 载体字典

        Returns:
            包含追踪上下文的载体
        """
        if OPENTELEMETRY_AVAILABLE:
            propagator = TraceContextTextMapPropagator()
            propagator.inject(carrier)
        return carrier

    def extract_context(self, carrier: Dict[str, str]):
        """从载体提取追踪上下文

        Args:
            carrier: 包含追踪上下文的载体

        Returns:
            追踪上下文
        """
        if OPENTELEMETRY_AVAILABLE:
            propagator = TraceContextTextMapPropagator()
            return propagator.extract(carrier)
        return None


class RequestTracingMiddleware:
    """请求追踪中间件"""

    def __init__(self, tracing_manager: TracingManager):
        """初始化请求追踪中间件

        Args:
            tracing_manager: 追踪管理器实例
        """
        self.tracing_manager = tracing_manager

    def create_request_span(
        self, request_id: str, operation_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> SpanInfo:
        """为请求创建追踪Span

        Args:
            request_id: 请求ID
            operation_name: 操作名称
            metadata: 请求元数据

        Returns:
            Span信息对象
        """
        tags = {"request_id": request_id, "type": "http_request"}
        if metadata:
            tags.update({k: str(v) for k, v in metadata.items()})

        with self.tracing_manager.start_span(operation_name, tags=tags) as span:
            return span


def get_tracing_manager() -> TracingManager:
    """获取追踪管理器单例

    Returns:
        追踪管理器实例
    """
    if not hasattr(get_tracing_manager, "_instance"):
        get_tracing_manager._instance = TracingManager()
    return get_tracing_manager._instance


def trace_function(
    operation_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable:
    """追踪函数的便捷装饰器

    Args:
        operation_name: 操作名称
        tags: 标签
        attributes: 属性

    Returns:
        装饰器函数
    """
    return get_tracing_manager().trace_function(operation_name, tags, attributes)
