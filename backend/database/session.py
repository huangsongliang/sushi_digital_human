"""数据库会话管理"""

from typing import Any, AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.database.pool import DatabasePoolMonitor, OptimizedDatabaseSessionManager


class DatabaseSessionManager:
    """数据库会话管理器"""

    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init(self):
        """初始化数据库连接"""
        if settings.database_url:
            self._engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=False,  # aiomysql 兼容性问题，禁用心跳检查
                pool_reset_on_return='rollback',  # 归还连接时回滚
            )
            self._session_factory = sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            self._monitor = DatabasePoolMonitor(self._engine)

    async def get_session(self) -> AsyncGenerator[Optional[AsyncSession], None]:
        """获取数据库会话"""
        if not self._session_factory:
            yield None
            return

        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self):
        """创建所有表"""
        if self._engine:
            from backend.database.models import Base

            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        """删除所有表"""
        if self._engine:
            from backend.database.models import Base

            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

    async def dispose(self):
        """释放数据库连接"""
        if self._engine:
            await self._engine.dispose()


# 全局数据库会话管理器实例
db_manager = DatabaseSessionManager()


async def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    async for session in db_manager.get_session():
        if session:
            yield session


# 初始化数据库连接
def initialize_database():
    """初始化数据库"""
    db_manager.init()


# 异步初始化数据库
async def async_initialize_database():
    """异步初始化数据库"""
    db_manager.init()
    await db_manager.create_tables()


class DBSessionContext:
    """数据库会话上下文管理器"""

    def __init__(self):
        self.session = None

    async def __aenter__(self):
        if not db_manager._session_factory:
            db_manager.init()
        self.session = db_manager._session_factory()
        return self.session

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        if self.session:
            try:
                if exc_type is None:
                    await self.session.commit()
                else:
                    await self.session.rollback()
            finally:
                await self.session.close()


def get_db_session():
    """获取数据库会话（异步上下文管理器）"""
    return DBSessionContext()
