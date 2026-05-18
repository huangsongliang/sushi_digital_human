"""健康检查模块单元测试"""
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
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK"
        )
        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY

    def test_component_health_with_all_fields(self):
        health = ComponentHealth(
            name="test",
            status=HealthStatus.DEGRADED,
            message="Warning",
            latency_ms=100.0
        )
        assert health.latency_ms == 100.0


class TestHealthChecker:
    """健康检查器测试"""

    def test_health_checker_creation(self):
        checker = HealthChecker()
        assert checker is not None

    def test_get_overall_status_empty(self):
        checker = HealthChecker()
        status = checker.get_overall_status()
        assert status == HealthStatus.DEGRADED

    def test_get_health_report(self):
        checker = HealthChecker()
        report = checker.get_health_report()
        assert report is not None
        assert "status" in report


class TestGracefulShutdownManager:
    """优雅关闭管理器测试"""

    def test_shutdown_manager_creation(self):
        manager = GracefulShutdownManager()
        assert manager is not None

    def test_is_shutting_down(self):
        manager = GracefulShutdownManager()
        assert manager.is_shutting_down is False

    def test_active_requests(self):
        manager = GracefulShutdownManager()
        assert manager.active_requests == 0


class TestGlobalInstances:
    """全局实例测试"""

    def test_health_checker_instance(self):
        assert health_checker is not None
        assert isinstance(health_checker, HealthChecker)

    def test_shutdown_manager_instance(self):
        assert shutdown_manager is not None
        assert isinstance(shutdown_manager, GracefulShutdownManager)
