"""性能监控模块单元测试"""
from backend.utils.performance import (
    Timer,
    PerformanceMonitor,
    record_request,
    record_error,
    performance_monitor
)


class TestTimer:
    """计时器测试"""

    def test_timer_start_stop(self):
        timer = Timer()
        timer.start()
        timer.stop()
        assert timer.elapsed >= 0

    def test_timer_context_manager(self):
        timer = Timer()
        with timer.measure():
            pass
        assert timer.elapsed >= 0

    def test_timer_reset(self):
        timer = Timer()
        timer.start()
        timer.stop()
        timer.reset()
        assert timer.elapsed == 0


class TestPerformanceMonitor:
    """性能监控测试"""

    def test_record(self):
        monitor = PerformanceMonitor()
        monitor.record("test_op", 0.5)
        metrics = monitor.get_metrics()
        assert "test_op" in metrics["operations"]

    def test_increment_request_count(self):
        monitor = PerformanceMonitor()
        monitor.increment_request_count()
        metrics = monitor.get_metrics()
        assert metrics["request_count"] == 1

    def test_get_metrics(self):
        monitor = PerformanceMonitor()
        metrics = monitor.get_metrics()
        assert metrics is not None
        assert "request_count" in metrics

    def test_reset(self):
        monitor = PerformanceMonitor()
        monitor.increment_request_count()
        monitor.reset()
        metrics = monitor.get_metrics()
        assert metrics["request_count"] == 0


class TestPrometheusMetrics:
    """Prometheus指标测试"""

    def test_record_request(self):
        record_request("test_endpoint", "GET", "200", 0.5)

    def test_record_error(self):
        record_error("test_error", "test_endpoint")


class TestGlobalPerformanceMonitor:
    """全局性能监控器测试"""

    def test_global_monitor(self):
        assert performance_monitor is not None
        assert isinstance(performance_monitor, PerformanceMonitor)
