"""多级缓存模块 - L1 本地内存 + L2 Redis"""

import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from collections import OrderedDict
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """本地 LRU 缓存 - 作为 L1 缓存"""

    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 300):
        """
        Args:
            maxsize: 最大缓存项数
            ttl_seconds: 默认过期时间（秒）
        """
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self.hit_count = 0
        self.miss_count = 0

    def _is_expired(self, entry: tuple) -> bool:
        """检查缓存项是否过期"""
        _, expires_at = entry
        return datetime.now() > expires_at

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        if key not in self.cache:
            self.miss_count += 1
            return None

        entry = self.cache[key]
        if self._is_expired(entry):
            del self.cache[key]
            self.miss_count += 1
            return None

        self.cache.move_to_end(key)
        self.hit_count += 1
        return entry[0]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """设置缓存项"""
        if len(self.cache) >= self.maxsize:
            oldest = next(iter(self.cache))
            del self.cache[oldest]

        ttl = ttl_seconds if ttl_seconds else self.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expires_at)
        self.cache.move_to_end(key)

    def delete(self, key: str):
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """清空缓存"""
        self.cache.clear()

    @property
    def stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total,
            "hit_rate": round(hit_rate, 2),
            "current_size": len(self.cache),
            "max_size": self.maxsize,
        }


class MultiLevelCache:
    """多级缓存管理器

    L1: 本地 LRU 缓存 - 低延迟访问
    L2: Redis 缓存 - 大容量、分布式共享
    """

    def __init__(self):
        self.l1_cache = LRUCache(maxsize=1000, ttl_seconds=300)
        self.l2_cache = redis_conn
        self.key_prefix = "mlcache:"
        self._warmup_completed = False
        self._warmup_items = []

    def _generate_key(self, *args, **kwargs) -> str:
        """生成唯一缓存键"""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    async def get(
        self, key: str, use_l1: bool = True, use_l2: bool = True
    ) -> Optional[Any]:
        """获取缓存值（多级查询）"""
        full_key = self.key_prefix + key

        if use_l1:
            l1_result = self.l1_cache.get(full_key)
            if l1_result is not None:
                logger.debug(f"L1 cache hit: {key}")
                return l1_result

        if use_l2:
            l2_result = await self.l2_cache.get(full_key)
            if l2_result is not None:
                logger.debug(f"L2 cache hit: {key}")
                if use_l1:
                    self.l1_cache.set(full_key, l2_result)
                return l2_result

        logger.debug(f"Cache miss: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 3600,
        write_l1: bool = True,
        write_l2: bool = True,
    ):
        """设置缓存值"""
        full_key = self.key_prefix + key

        if write_l1:
            self.l1_cache.set(full_key, value, ttl_seconds)

        if write_l2:
            await self.l2_cache.set(full_key, value, ttl=ttl_seconds)

    async def delete(self, key: str):
        """删除缓存"""
        full_key = self.key_prefix + key
        self.l1_cache.delete(full_key)
        await self.l2_cache.delete(full_key)

    async def clear(self):
        """清空所有缓存"""
        self.l1_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        l1_stats = self.l1_cache.stats
        return {"l1": l1_stats, "total_hit_rate": l1_stats["hit_rate"]}

    def add_warmup_item(self, key: str, value: Any, ttl_seconds: int = 86400):
        """添加预热项"""
        self._warmup_items.append({"key": key, "value": value, "ttl": ttl_seconds})

    async def warmup(self):
        """执行缓存预热"""
        if self._warmup_completed:
            logger.info("Cache warmup already completed")
            return

        msg = f"Starting cache warmup with {len(self._warmup_items)} items"
        logger.info(msg)

        for item in self._warmup_items:
            try:
                await self.set(
                    key=item["key"], value=item["value"], ttl_seconds=item["ttl"]
                )
            except Exception as e:
                logger.error(f"Failed to warmup {item['key']}: {e}")

        self._warmup_completed = True
        logger.info("Cache warmup completed")

    @property
    def warmup_completed(self) -> bool:
        return self._warmup_completed


multi_level_cache = MultiLevelCache()
