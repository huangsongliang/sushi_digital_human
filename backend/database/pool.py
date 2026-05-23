"""
数据库连接池优化模块
提供连接池监控、健康检查和性能优化功能
"""

import asyncio
import time
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class DatabasePoolMonitor:
    """数据库连接池监控器"""

    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "connection_timeouts": 0,
            "pool_overflow_used": 0,
        }
        self._start_time = time.time()
        self._last_health_check: Optional[float] = None
        self._lock = asyncio.Lock()

    async def record_request(self, success: bool, timeout: bool = False, overflow: bool = False):
        """记录请求统计"""
        async with self._lock:
            self._stats["total_requests"] += 1
            if success:
                self._stats["successful_requests"] += 1
            else:
                self._stats["failed_requests"] += 1
            if timeout:
                self._stats["connection_timeouts"] += 1
            if overflow:
                self._stats["pool_overflow_used"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self._start_time
        success_rate = 0.0
        if self._stats["total_requests"] > 0:
            success_rate = (self._stats["successful_requests"] / self._stats["total_requests"]) * 100

        return {
            "uptime_seconds": uptime,
            "total_requests": self._stats["total_requests"],
            "successful_requests": self._stats["successful_requests"],
            "failed_requests": self._stats["failed_requests"],
            "connection_timeouts": self._stats["connection_timeouts"],
            "pool_overflow_used": self._stats["pool_overflow_used"],
            "success_rate_percent": success_rate,
            "requests_per_second": self._stats["total_requests"] / uptime if uptime > 0 else 0,
        }

    async def check_health(self) -> bool:
        """检查数据库连接池健康状态"""
        try:
            async with self.engine.connect() as conn:
                await conn.execute("SELECT 1")
            self._last_health_check = time.time()
            logger.debug("数据库连接池健康检查通过")
            return True
        except Exception as e:
            logger.error(f"数据库连接池健康检查失败: {str(e)}")
            return False


class OptimizedDatabaseSessionManager:
    """优化的数据库会话管理器"""

    def __init__(self):
        self._engine = None
        self._session_factory = None
        self._monitor = None

    def init(self, database_url: str, **kwargs):
        """初始化优化的数据库连接池"""
        # 优化的连接池配置
        pool_config = {
            "echo": kwargs.get("echo", False),
            "pool_size": kwargs.get("pool_size", 10),  # 核心连接数
            "max_overflow": kwargs.get("max_overflow", 20),  # 最大溢出连接数
            "pool_timeout": kwargs.get("pool_timeout", 30),  # 获取连接超时时间
            "pool_recycle": kwargs.get("pool_recycle", 1800),  # 连接回收时间（30分钟）
            "pool_pre_ping": kwargs.get("pool_pre_ping", False),  # 禁用预检查（aiomysql不兼容）
            "pool_reset_on_return": kwargs.get("pool_reset_on_return", "rollback"),  # 归还连接时回滚
            "future": True,
        }

        logger.info(f"初始化数据库连接池，配置: {pool_config}")

        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker

        self._engine = create_async_engine(database_url, **pool_config)
        self._session_factory = sessionmaker(
            bind=self._engine,
            class_=kwargs.get("class_", AsyncSession),
            expire_on_commit=kwargs.get("expire_on_commit", False),
            autocommit=kwargs.get("autocommit", False),
            autoflush=kwargs.get("autoflush", False),
        )

        # 初始化监控器
        self._monitor = DatabasePoolMonitor(self._engine)
        logger.info("数据库连接池初始化完成")

    @property
    def engine(self):
        return self._engine

    @property
    def session_factory(self):
        return self._session_factory

    @property
    def monitor(self):
        return self._monitor

    async def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if self._monitor:
            return self._monitor.get_stats()
        return {}

    async def check_health(self) -> bool:
        """检查健康状态"""
        if self._monitor:
            return await self._monitor.check_health()
        return False

    async def dispose(self):
        """释放连接池资源"""
        if self._engine:
            await self._engine.dispose()
            logger.info("数据库连接池已释放")


# 全局优化的数据库会话管理器
_opt_db_manager: Optional[OptimizedDatabaseSessionManager] = None


def get_optimized_db_manager() -> OptimizedDatabaseSessionManager:
    """获取优化的数据库管理器实例"""
    global _opt_db_manager
    if _opt_db_manager is None:
        _opt_db_manager = OptimizedDatabaseSessionManager()
    return _opt_db_manager
