"""缓存管理模块 - Redis 实现"""
import json
import hashlib
from typing import Any, Optional
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器"""
    
    KEY_PREFIX = "cache:"
    DEFAULT_TTL = 3600  # 默认 1 小时过期
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """生成缓存键"""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        hash_value = hashlib.md5(data.encode()).hexdigest()
        return hash_value
    
    async def get(self, query: str, use_rag: bool = True) -> Optional[Any]:
        """获取缓存"""
        try:
            key = self.generate_key(query, use_rag)
            cache_key = f"{self.KEY_PREFIX}{key}"
            
            client = await redis_conn.get_client()
            cached = await client.get(cache_key)
            
            if cached:
                logger.info(f"缓存命中: key={key[:16]}...")
                return json.loads(cached)
            
            logger.info(f"缓存未命中: key={key[:16]}...")
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None
    
    async def set(
        self, 
        query: str, 
        result: Any, 
        use_rag: bool = True, 
        ttl: int = DEFAULT_TTL
    ) -> bool:
        """设置缓存"""
        try:
            key = self.generate_key(query, use_rag)
            cache_key = f"{self.KEY_PREFIX}{key}"
            
            client = await redis_conn.get_client()
            await client.setex(
                cache_key,
                ttl,
                json.dumps(result, ensure_ascii=False)
            )
            
            logger.info(f"缓存已设置: key={key[:16]}..., ttl={ttl}s")
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete(self, query: str, use_rag: bool = True) -> bool:
        """删除缓存"""
        try:
            key = self.generate_key(query, use_rag)
            cache_key = f"{self.KEY_PREFIX}{key}"
            
            client = await redis_conn.get_client()
            await client.delete(cache_key)
            
            logger.info(f"缓存已删除: key={key[:16]}...")
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            client = await redis_conn.get_client()
            keys = await client.keys(f"{self.KEY_PREFIX}*")
            
            if keys:
                await client.delete(*keys)
                logger.info(f"已清空 {len(keys)} 条缓存")
            
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False


cache_manager = CacheManager()
