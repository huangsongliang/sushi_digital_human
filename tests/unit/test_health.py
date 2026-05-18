"""健康检查模块单元测试"""
import pytest
from datetime import datetime
from backend.utils.health import (
    HealthStatus,
    ComponentHealth,
    HealthChecker,
    GracefulShutdownManager,
    health_checker,
    shutdown_manager
)


class TestHealthStatus:
    """健康状态枚举测试"""
    
    def test_health_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestComponentHealth:
    """组件健康状态测试"""
    
    def test_component_health_creation(self):
        component = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="正常"
        )
        assert component.name == "test"
        assert component.status == HealthStatus.HEALTHY
        assert component.message == "正常"
        assert component.latency_ms is None
        assert component.last_checked is None
    
    def test_component_health_with_all_fields(self):
        now = datetime.now()
        component = ComponentHealth(
            name="test",
            status=HealthStatus.UNHEALTHY,
            message="失败",
            latency_ms=123.45,
            last_checked=now
        )
        assert component.latency_ms == 123.45
        assert component.last_checked == now


class TestHealthChecker:
    """健康检查器测试"""
    
    def test_health_checker_creation(self):
        checker = HealthChecker()
        assert checker._auto_recovery_enabled is True
        assert checker._recovery_cooldown == 60
    
    def test_get_overall_status_empty(self):
        checker = HealthChecker()
        assert checker.get_overall_status() == HealthStatus.DEGRADED
    
    def test_get_overall_status_all_healthy(self):
        checker = HealthChecker()
        checker._checks = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY, message="ok"),
            ComponentHealth(name="redis", status=HealthStatus.HEALTHY, message="ok")
        ]
        assert checker.get_overall_status() == HealthStatus.HEALTHY
    
    def test_get_overall_status_with_degraded(self):
        checker = HealthChecker()
        checker._checks = [
            ComponentHealth(name="db", status=HealthStatus.HEALTHY, message="ok"),
            ComponentHealth(name="llm", status=HealthStatus.DEGRADED, message="warning")
        ]
        assert checker.get_overall_status() == HealthStatus.DEGRADED
    
    def test_get_overall_status_with_unhealthy(self):
        checker = HealthChecker()
        checker._checks = [
            ComponentHealth(name="db", status=HealthStatus.UNHEALTHY, message="error"),
            ComponentHealth(name="redis", status=HealthStatus.HEALTHY, message="ok")
        ]
        assert checker.get_overall_status() == HealthStatus.UNHEALTHY
    
    def test_get_health_report(self):
        checker = HealthChecker()
        checker._checks = [
            ComponentHealth(name="test", status=HealthStatus.HEALTHY, message="ok")
        ]
        checker._last_check_time = datetime.now()
        
        report = checker.get_health_report()
        assert "status" in report
        assert "checks" in report
        assert "timestamp" in report


class TestGracefulShutdownManager:
    """优雅关闭管理器测试"""
    
    def test_shutdown_manager_creation(self):
        manager = GracefulShutdownManager()
        assert manager._max_wait_time == 30
        assert manager._active_requests == 0
    
    def test_increment_decrement_request_count(self):
        manager = GracefulShutdownManager()
        assert manager.active_requests == 0
        
        manager.increment_request_count()
        assert manager.active_requests == 1
        
        manager.increment_request_count()
        assert manager.active_requests == 2
        
        manager.decrement_request_count()
        assert manager.active_requests == 1
    
    def test_is_shutting_down(self):
        manager = GracefulShutdownManager()
        assert manager.is_shutting_down is False
        
        manager.initiate_shutdown()
        assert manager.is_shutting_down is True


class TestGlobalInstances:
    """全局实例测试"""
    
    def test_health_checker_instance(self):
        assert health_checker is not None
        assert isinstance(health_checker, HealthChecker)
    
    def test_shutdown_manager_instance(self):
        assert shutdown_manager is not None
        assert isinstance(shutdown_manager, GracefulShutdownManager)