"""Redis 连接管理模块"""
import redis.asyncio as redis
from typing import Optional
from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)
assert logger is not None, "Logger cannot be None"


class RedisConnection:
    """Redis 连接管理器（单例）"""
    
    _instance: Optional['RedisConnection'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_client(self) -> redis.Redis:
        """获取 Redis 客户端（懒加载）"""
        if self._client is None:
            logger.info("初始化 Redis 连接...")
            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            logger.info("Redis 连接初始化成功")
        return self._client
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Redis 连接已关闭")
    
    async def ping(self) -> bool:
        """检查 Redis 连接"""
        try:
            client: redis.Redis = await self.get_client()
            await client.ping()  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            return False


redis_conn = RedisConnection()
