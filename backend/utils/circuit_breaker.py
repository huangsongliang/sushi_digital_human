"""熔断器模块 - 防止服务雪崩"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(Enum):
    """熔断器状态"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """熔断器异常"""

    def __init__(self, message: str, breaker_name: str):
        super().__init__(message)
        self.breaker_name = breaker_name


class CircuitBreaker:
    """熔断器实现"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 20,
        success_threshold: int = 5,
        reset_timeout: int = 60,
        max_concurrent_requests: int = 100,
    ):
        """
        Args:
            name: 熔断器名称（用于标识和日志）
            failure_threshold: 失败阈值，超过此值触发熔断
            success_threshold: 半开状态下的成功阈值
            reset_timeout: 熔断后自动尝试恢复的时间（秒）
            max_concurrent_requests: 最大并发请求数
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.reset_timeout = reset_timeout
        self.max_concurrent_requests = max_concurrent_requests

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        self._concurrent_requests = 0

        self._total_requests = 0
        self._total_failures = 0
        self._total_successes = 0
        self._tripped_count = 0

        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        """获取当前状态（带自动恢复逻辑）"""
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._last_failure_time >= self.reset_timeout:
                msg = f"Circuit breaker {self.name}: attempting recovery"
                logger.info(msg)
                self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "success_count": self._success_count,
            "success_threshold": self.success_threshold,
            "reset_timeout": self.reset_timeout,
            "total_requests": self._total_requests,
            "total_successes": self._total_successes,
            "total_failures": self._total_failures,
            "tripped_count": self._tripped_count,
            "concurrent_requests": self._concurrent_requests,
        }

    async def _record_success(self):
        """记录成功"""
        async with self._lock:
            self._success_count += 1
            self._total_successes += 1
            self._failure_count = 0

            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._success_count >= self.success_threshold:
                    msg = f"Circuit breaker {self.name}: recovered"
                    logger.info(msg)
                    self._state = CircuitBreakerState.CLOSED
                    self._success_count = 0

    async def _record_failure(self):
        """记录失败"""
        async with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._success_count = 0
            self._last_failure_time = time.time()

            if self._failure_count >= self.failure_threshold:
                if self._state != CircuitBreakerState.OPEN:
                    logger.warning(f"Circuit breaker {self.name} tripped!")
                    self._tripped_count += 1
                self._state = CircuitBreakerState.OPEN

    async def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """执行受保护的调用"""
        current_state = self.state

        if current_state == CircuitBreakerState.OPEN:
            raise CircuitBreakerError(f"Circuit breaker {self.name} is open, request rejected", self.name)

        if self._concurrent_requests >= self.max_concurrent_requests:
            raise CircuitBreakerError(f"Circuit breaker {self.name} concurrent limit exceeded", self.name)

        self._total_requests += 1
        self._concurrent_requests += 1

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except CircuitBreakerError:
            raise
        except Exception:
            await self._record_failure()
            raise
        finally:
            self._concurrent_requests -= 1

    def reset(self):
        """重置熔断器状态"""
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0
        logger.info(f"Circuit breaker {self.name} reset")


class CircuitBreakerManager:
    """熔断器管理器 - 管理多个熔断器"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 20,
        success_threshold: int = 5,
        reset_timeout: int = 60,
    ) -> CircuitBreaker:
        """获取或创建熔断器"""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                success_threshold=success_threshold,
                reset_timeout=reset_timeout,
            )
        return self._breakers[name]

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器的统计信息"""
        return {name: breaker.stats for name, breaker in self._breakers.items()}

    def reset_all(self):
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()


circuit_breaker_manager = CircuitBreakerManager()

llm_breaker = CircuitBreaker(name="llm_api", failure_threshold=10, success_threshold=3, reset_timeout=30)

embedding_breaker = CircuitBreaker(name="embedding_api", failure_threshold=15, success_threshold=5, reset_timeout=45)

redis_breaker = CircuitBreaker(name="redis", failure_threshold=5, success_threshold=3, reset_timeout=10)
