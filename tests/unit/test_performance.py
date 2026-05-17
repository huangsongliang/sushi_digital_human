"""性能监控模块单元测试"""

import pytest
from backend.utils.performance import (
    PerformanceMonitor,
    Timer,
    generate_prometheus_metrics,
    record_request,
    record_error
)


class TestTimer:
    """计时器测试"""
    
    def test_timer_start_stop(self):
        """测试计时器启动和停止"""
        timer = Timer("test")
        timer.start()
        import time
        time.sleep(0.01)
        elapsed = timer.stop()
        assert elapsed > 0
        assert isinstance(elapsed, float)
    
    def test_timer_context_manager(self):
        """测试计时器上下文管理器"""
        with Timer("context_test").measure() as timer:
            import time
            time.sleep(0.01)
        assert timer.elapsed > 0
    
    def test_timer_reset(self):
        """测试计时器重置"""
        timer = Timer("test")
        timer.start()
        import time
        time.sleep(0.01)
        timer.stop()
        assert timer.elapsed > 0
        timer.reset()
        assert timer.elapsed == 0.0


class TestPerformanceMonitor:
    """性能监控器测试"""
    
    def test_record_operation(self):
        """测试记录操作耗时"""
        monitor = PerformanceMonitor()
        monitor.record("test_op", 0.1)
        monitor.record("test_op", 0.2)
        metrics = monitor.get_metrics()
        assert "test_op" in metrics["operations"]
        assert metrics["operations"]["test_op"]["count"] == 2
    
    def test_increment_request_count(self):
        """测试增加请求计数"""
        monitor = PerformanceMonitor()
        assert monitor._request_count == 0
        monitor.increment_request_count()
        assert monitor._request_count == 1
    
    def test_add_request_time(self):
        """测试添加请求耗时"""
        monitor = PerformanceMonitor()
        assert monitor._total_time == 0.0
        monitor.add_request_time(0.5)
        assert monitor._total_time == 0.5
    
    def test_get_metrics(self):
        """测试获取指标"""
        monitor = PerformanceMonitor()
        monitor.record("op1", 0.1)
        monitor.record("op1", 0.2)
        monitor.increment_request_count()
        monitor.add_request_time(0.3)
        
        metrics = monitor.get_metrics()
        
        assert "uptime" in metrics
        assert "request_count" in metrics
        assert "avg_request_time" in metrics
        assert "operations" in metrics
        assert metrics["request_count"] == 1
    
    def test_calculate_percentile(self):
        """测试百分位数计算"""
        monitor = PerformanceMonitor()
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        p95 = monitor._calculate_percentile(values, 95)
        assert p95 == 10
        p50 = monitor._calculate_percentile(values, 50)
        assert p50 == 6  # 索引 = 10 * 50 / 100 = 5，取第6个元素
    
    def test_reset(self):
        """测试重置指标"""
        monitor = PerformanceMonitor()
        monitor.record("test", 0.1)
        monitor.increment_request_count()
        monitor.add_request_time(0.5)
        
        monitor.reset()
        
        assert monitor._request_count == 0
        assert monitor._total_time == 0.0
        assert len(monitor._metrics) == 0


class TestPrometheusMetrics:
    """Prometheus 指标测试"""
    
    def test_generate_metrics(self):
        """测试生成 Prometheus 指标"""
        metrics = generate_prometheus_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0
    
    def test_record_request(self):
        """测试记录请求指标"""
        record_request("/api/chat", "POST", "success", 0.5)
    
    def test_record_error(self):
        """测试记录错误指标"""
        record_error("ValueError", "/api/chat")
