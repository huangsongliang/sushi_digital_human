"""数据库会话管理"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings


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
                echo=False, pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=1800
            )
            self._session_factory = sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
    
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
