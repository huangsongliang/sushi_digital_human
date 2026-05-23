"""指标收集器模块
收集系统指标和业务指标，支持自定义指标
"""

import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import psutil

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SystemMetrics:
    """系统指标数据类"""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    thread_count: int


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.custom_metrics: Dict[str, List[float]] = defaultdict(list)
        self.business_metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.collection_history: List[SystemMetrics] = []
        self.max_history_size = 1000

    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net_io = psutil.net_io_counters()

            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_percent=disk.percent,
                disk_used_gb=disk.used / (1024 * 1024 * 1024),
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_sent_mb=net_io.bytes_sent / (1024 * 1024),
                network_recv_mb=net_io.bytes_recv / (1024 * 1024),
                process_count=len(psutil.pids()),
                thread_count=self._get_total_threads(),
            )

            self.collection_history.append(metrics)
            if len(self.collection_history) > self.max_history_size:
                self.collection_history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"收集系统指标失败: {str(e)}")
            raise

    def _get_total_threads(self) -> int:
        """获取总线程数"""
        total_threads = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                total_threads += proc.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total_threads

    def record_custom_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录自定义指标"""
        self.custom_metrics[metric_name].append(value)

        if len(self.custom_metrics[metric_name]) > self.max_history_size:
            self.custom_metrics[metric_name].pop(0)

        if tags:
            self.business_metrics[f"{metric_name}_with_tags"].append(
                {
                    "value": value,
                    "tags": tags,
                    "timestamp": time.time(),
                }
            )

    def record_business_metric(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """记录业务指标"""
        metric_entry = {
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }

        self.business_metrics[metric_name].append(metric_entry)

        if len(self.business_metrics[metric_name]) > self.max_history_size:
            self.business_metrics[metric_name].pop(0)

    def get_metric_statistics(self, metric_name: str, window_seconds: int = 300) -> Dict[str, float]:
        """获取指标统计信息"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        if metric_name in self.custom_metrics:
            values = [v for v in self.custom_metrics[metric_name] if v >= cutoff_time]
        elif metric_name in self.business_metrics:
            values = [
                entry["value"] for entry in self.business_metrics[metric_name] if entry["timestamp"] >= cutoff_time
            ]
        else:
            return {}

        if not values:
            return {}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "latest": values[-1],
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有当前指标"""
        system_metrics = self.collect_system_metrics()

        return {
            "system": asdict(system_metrics),
            "custom_metrics": {name: self.get_metric_statistics(name) for name in self.custom_metrics.keys()},
            "business_metrics": {name: self.get_metric_statistics(name) for name in self.business_metrics.keys()},
        }

    def get_metric_trend(self, metric_name: str, points: int = 10) -> List[float]:
        """获取指标趋势"""
        if metric_name in self.custom_metrics:
            values = self.custom_metrics[metric_name][-points:]
        elif metric_name in self.business_metrics:
            values = [entry["value"] for entry in self.business_metrics[metric_name][-points:]]
        else:
            return []

        return values

    def get_system_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        metrics = self.collect_system_metrics()

        status = {
            "cpu": ("healthy" if metrics.cpu_percent < 80 else "warning" if metrics.cpu_percent < 95 else "critical"),
            "memory": (
                "healthy" if metrics.memory_percent < 80 else "warning" if metrics.memory_percent < 95 else "critical"
            ),
            "disk": (
                "healthy" if metrics.disk_percent < 80 else "warning" if metrics.disk_percent < 95 else "critical"
            ),
        }

        overall = (
            "healthy"
            if all(s == "healthy" for s in status.values())
            else "warning" if "critical" not in status.values() else "critical"
        )

        return {
            "status": overall,
            "details": status,
            "timestamp": metrics.timestamp,
        }

    def clear_old_metrics(self, max_age_seconds: int = 3600):
        """清理旧指标数据"""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        for metric_name in list(self.business_metrics.keys()):
            self.business_metrics[metric_name] = [
                entry for entry in self.business_metrics[metric_name] if entry["timestamp"] >= cutoff_time
            ]

        logger.info("清理旧指标完成")


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        logger.info("指标收集器已初始化")
    return _metrics_collector
