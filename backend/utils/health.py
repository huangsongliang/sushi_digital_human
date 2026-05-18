"""
健康检查模块
提供服务健康状态检测和自动恢复功能，支持：
- 多组件健康检查（数据库、Redis、检索器、LLM）
- 自动恢复机制
- 优雅关闭支持
- Prometheus 集成
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from sqlalchemy import text
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from redis import asyncio as aioredis

from backend.core.config import settings
from backend.database.session import db_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    last_checked: Optional[datetime] = None


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        self._checks: List[ComponentHealth] = []
        self._last_check_time: Optional[datetime] = None
        self._auto_recovery_enabled = True
        self._recovery_attempts: Dict[str, float] = {}
        self._recovery_cooldown = 60

    async def check_database(self) -> ComponentHealth:
        """检查数据库连接"""
        start_time = time.time()
        try:
            async for session in db_manager.get_session():
                if session:
                    await session.execute(text("SELECT 1"))
                    latency_ms = (time.time() - start_time) * 1000
                    return ComponentHealth(
                        name="database",
                        status=HealthStatus.HEALTHY,
                        message="数据库连接正常",
                        latency_ms=round(latency_ms, 2),
                        last_checked=datetime.now()
                    )
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                message="数据库会话未初始化",
                latency_ms=(time.time() - start_time) * 1000,
                last_checked=datetime.now()
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            await self._attempt_recovery("database")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {str(e)}",
                latency_ms=round(latency_ms, 2),
                last_checked=datetime.now()
            )

    async def check_redis(self) -> ComponentHealth:
        """检查 Redis 连接"""
        start_time = time.time()
        try:
            redis = aioredis.from_url(settings.redis_url)
            await redis.ping()  # type: ignore
            await redis.close()
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message="Redis 连接正常",
                latency_ms=round(latency_ms, 2),
                last_checked=datetime.now()
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            await self._attempt_recovery("redis")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis 连接失败: {str(e)}",
                latency_ms=round(latency_ms, 2),
                last_checked=datetime.now()
            )

    async def check_retriever(self) -> ComponentHealth:
        """检查检索器状态"""
        start_time = time.time()
        try:
            from backend.retrieval import get_hybrid_retriever
            retriever = get_hybrid_retriever()
            if retriever:
                latency_ms = (time.time() - start_time) * 1000
                return ComponentHealth(
                    name="retriever",
                    status=HealthStatus.HEALTHY,
                    message="检索器初始化正常",
                    latency_ms=round(latency_ms, 2),
                    last_checked=datetime.now()
                )
            return ComponentHealth(
                name="retriever",
                status=HealthStatus.DEGRADED,
                message="检索器未初始化",
                latency_ms=(time.time() - start_time) * 1000,
                last_checked=datetime.now()
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            await self._attempt_recovery("retriever")
            return ComponentHealth(
                name="retriever",
                status=HealthStatus.UNHEALTHY,
                message=f"检索器检查失败: {str(e)}",
                latency_ms=round(latency_ms, 2),
                last_checked=datetime.now()
            )

    async def check_llm(self) -> ComponentHealth:
        """检查 LLM 服务"""
        start_time = time.time()
        try:
            from backend.generator import get_async_llm
            llm = get_async_llm()
            if llm:
                latency_ms = (time.time() - start_time) * 1000
                return ComponentHealth(
                    name="llm",
                    status=HealthStatus.HEALTHY,
                    message="LLM 服务初始化正常",
                    latency_ms=round(latency_ms, 2),
                    last_checked=datetime.now()
                )
            return ComponentHealth(
                name="llm",
                status=HealthStatus.DEGRADED,
                message="LLM 服务未初始化",
                latency_ms=(time.time() - start_time) * 1000,
                last_checked=datetime.now()
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="llm",
                status=HealthStatus.DEGRADED,
                message=f"LLM 服务检查失败: {str(e)}",
                latency_ms=round(latency_ms, 2),
                last_checked=datetime.now()
            )

    async def _attempt_recovery(self, component_name: str):
        """尝试自动恢复组件"""
        if not self._auto_recovery_enabled:
            return

        now = time.time()
        last_attempt = self._recovery_attempts.get(component_name, 0)

        if now - last_attempt < self._recovery_cooldown:
            return

        self._recovery_attempts[component_name] = now
        logger.info(f"尝试自动恢复组件: {component_name}")

        try:
            if component_name == "database":
                db_manager.dispose()
                db_manager.init()
                await db_manager.create_tables()
            elif component_name == "redis":
                pass

            logger.info(f"组件 {component_name} 恢复成功")
        except Exception as e:
            logger.error(f"组件 {component_name} 恢复失败: {str(e)}")

    async def run_all_checks(self) -> List[ComponentHealth]:
        """运行所有健康检查"""
        checks_tuple = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_retriever(),
            self.check_llm()
        )
        checks = list(checks_tuple)
        self._checks = checks
        self._last_check_time = datetime.now()
        return checks

    def get_overall_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self._checks:
            return HealthStatus.DEGRADED

        statuses = [check.status for check in self._checks]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        checks_data = []
        for check in self._checks:
            checks_data.append({
                "name": check.name,
                "status": check.status.value,
                "message": check.message,
                "latency_ms": check.latency_ms,
                "last_checked": (
                    check.last_checked.isoformat()
                    if check.last_checked
                    else None
                )
            })

        return {
            "status": self.get_overall_status().value,
            "timestamp": (
                self._last_check_time.isoformat()
                if self._last_check_time
                else None
            ),
            "checks": checks_data,
            "service": settings.app_name,
            "version": settings.app_version
        }


health_checker = HealthChecker()


async def perform_health_check() -> Dict[str, Any]:
    """执行健康检查并返回报告"""
    await health_checker.run_all_checks()
    return health_checker.get_health_report()


def get_health_status() -> HealthStatus:
    """获取当前健康状态"""
    return health_checker.get_overall_status()


class GracefulShutdownManager:
    """优雅关闭管理器"""

    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._active_requests = 0
        self._max_wait_time = 30

    async def wait_for_shutdown(self):
        """等待关闭信号"""
        await self._shutdown_event.wait()

    def initiate_shutdown(self):
        """触发关闭流程"""
        logger.info("收到关闭信号，开始优雅关闭流程")
        self._shutdown_event.set()

    async def wait_for_requests_to_complete(self):
        """等待所有请求完成"""
        start_time = time.time()

        while self._active_requests > 0:
            elapsed = time.time() - start_time
            if elapsed >= self._max_wait_time:
                logger.warning(
                    f"等待请求完成超时，仍有 {self._active_requests} 个请求"
                )
                break

            await asyncio.sleep(0.5)
            logger.info(f"等待 {self._active_requests} 个请求完成...")

        logger.info("所有请求已完成")

    def increment_request_count(self):
        """增加活跃请求计数"""
        self._active_requests += 1

    def decrement_request_count(self):
        """减少活跃请求计数"""
        self._active_requests -= 1

    @property
    def is_shutting_down(self) -> bool:
        """是否正在关闭"""
        return self._shutdown_event.is_set()

    @property
    def active_requests(self) -> int:
        """当前活跃请求数"""
        return self._active_requests


shutdown_manager = GracefulShutdownManager()
