"""缓存管理模块 - Redis 实现
优化内容：
1. 添加嵌入缓存（Embedding Cache）
2. 智能缓存策略（TTL 动态调整）
3. 批量缓存操作
4. 缓存预热机制
"""

import json
import hashlib
from typing import Any, Optional, List, Dict
from datetime import datetime
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)
assert logger is not None, "Logger cannot be None"


class CacheManager:
    """缓存管理器 - 支持多种缓存类型"""

    KEY_PREFIX = "cache:"
    EMBEDDING_KEY_PREFIX = "embed:"
    QUERY_STATS_KEY = "query:stats"

    # TTL 配置（秒）
    DEFAULT_TTL = 3600  # 默认 1 小时
    SHORT_TTL = 600  # 短缓存 10 分钟（频繁变化的数据）
    LONG_TTL = 86400  # 长缓存 24 小时（稳定数据，如嵌入）
    EMBEDDING_TTL = 604800  # 嵌入缓存 7 天

    def __init__(self):
        self._hit_count = 0
        self._miss_count = 0

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """生成缓存键（MD5 哈希）"""
        data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        hash_value = hashlib.md5(data.encode(), usedforsecurity=False).hexdigest()
        return hash_value

    @staticmethod
    def generate_embedding_key(text: str) -> str:
        """生成嵌入缓存键"""
        return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()

    # ============ 查询缓存 ============

    async def get(self, query: str, use_rag: bool = True) -> Optional[Any]:
        """获取查询缓存"""
        try:
            key = self.generate_key(query, use_rag)
            cache_key = f"{self.KEY_PREFIX}{key}"

            client = await redis_conn.get_client()
            cached = await client.get(cache_key)

            if cached:
                self._hit_count += 1
                await self._update_query_stats(query, hit=True)
                logger.debug(f"缓存命中: key={key[:16]}...")
                return json.loads(cached)

            self._miss_count += 1
            await self._update_query_stats(query, hit=False)
            logger.debug(f"缓存未命中: key={key[:16]}...")
            return None
        except Exception as e:
            logger.error(f"获取缓存失败: {e}")
            return None

    async def set(self, query: str, result: Any, use_rag: bool = True, ttl: int = DEFAULT_TTL) -> bool:
        """设置查询缓存（支持动态 TTL）"""
        try:
            key = self.generate_key(query, use_rag)
            cache_key = f"{self.KEY_PREFIX}{key}"

            client = await redis_conn.get_client()
            await client.setex(cache_key, ttl, json.dumps(result, ensure_ascii=False))

            logger.debug(f"缓存已设置: key={key[:16]}..., ttl={ttl}s")
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {e}")
            return False

    # ============ 嵌入缓存 ============

    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入缓存"""
        try:
            key = self.generate_embedding_key(text)
            cache_key = f"{self.EMBEDDING_KEY_PREFIX}{key}"

            client = await redis_conn.get_client()
            cached = await client.get(cache_key)

            if cached:
                logger.debug(f"嵌入缓存命中: {len(text)} chars")
                return json.loads(cached)

            logger.debug(f"嵌入缓存未命中: {len(text)} chars")
            return None
        except Exception as e:
            logger.error(f"获取嵌入缓存失败: {e}")
            return None

    async def set_embedding(self, text: str, embedding: List[float]) -> bool:
        """设置文本嵌入缓存"""
        try:
            key = self.generate_embedding_key(text)
            cache_key = f"{self.EMBEDDING_KEY_PREFIX}{key}"

            client = await redis_conn.get_client()
            await client.setex(cache_key, self.EMBEDDING_TTL, json.dumps(embedding))

            logger.debug(f"嵌入缓存已设置: {len(text)} chars")
            return True
        except Exception as e:
            logger.error(f"设置嵌入缓存失败: {e}")
            return False

    async def get_embeddings_batch(self, texts: List[str]) -> Dict[str, Optional[List[float]]]:
        """批量获取嵌入缓存"""
        try:
            keys = [f"{self.EMBEDDING_KEY_PREFIX}{self.generate_embedding_key(t)}" for t in texts]

            client = await redis_conn.get_client()
            cached_values = await client.mget(*keys)

            result = {}
            for text, cached in zip(texts, cached_values):
                if cached:
                    result[text] = json.loads(cached)
                else:
                    result[text] = None

            return result
        except Exception as e:
            logger.error(f"批量获取嵌入缓存失败: {e}")
            return {t: None for t in texts}

    async def set_embeddings_batch(self, items: Dict[str, List[float]]) -> int:
        """批量设置嵌入缓存"""
        try:
            client = await redis_conn.get_client()
            pipe = client.pipeline()  # type: ignore

            for text, embedding in items.items():
                key = f"{self.EMBEDDING_KEY_PREFIX}{self.generate_embedding_key(text)}"
                pipe.setex(key, self.EMBEDDING_TTL, json.dumps(embedding))

            results = await pipe.execute()  # type: ignore
            success_count = sum(1 for r in results if r)

            logger.info(f"批量嵌入缓存完成: {success_count}/{len(items)}")
            return success_count
        except Exception as e:
            logger.error(f"批量设置嵌入缓存失败: {e}")
            return 0

    # ============ 缓存统计 ============

    async def _update_query_stats(self, query: str, hit: bool):
        """更新查询统计（用于智能缓存策略）"""
        try:
            client = await redis_conn.get_client()
            timestamp = datetime.now().isoformat()

            # 记录查询频率
            await client.zincrby(self.QUERY_STATS_KEY, 1, query)

            # 设置过期时间（保留最近 30 天的统计）
            await client.expire(self.QUERY_STATS_KEY, 30 * 86400)
        except Exception as e:
            logger.debug(f"更新查询统计失败: {e}")

    async def get_hot_queries(self, limit: int = 10) -> List[str]:
        """获取热门查询（用于缓存预热）"""
        try:
            client = await redis_conn.get_client()
            result = await client.zrevrange(self.QUERY_STATS_KEY, 0, limit - 1)
            return [r.decode("utf-8") for r in result]
        except Exception as e:
            logger.error(f"获取热门查询失败: {e}")
            return []

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0

        return {
            "hits": self._hit_count,
            "misses": self._miss_count,
            "total": total,
            "hit_rate": round(hit_rate, 2),
        }

    # ============ 缓存管理 ============

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

            # 删除查询缓存
            query_keys = await client.keys(f"{self.KEY_PREFIX}*")
            if query_keys:
                await client.delete(*query_keys)

            # 删除嵌入缓存
            embed_keys = await client.keys(f"{self.EMBEDDING_KEY_PREFIX}*")
            if embed_keys:
                await client.delete(*embed_keys)

            # 重置统计
            self._hit_count = 0
            self._miss_count = 0

            logger.info(f"已清空 {len(query_keys)} 条查询缓存和 {len(embed_keys)} 条嵌入缓存")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False

    async def warm_up_cache(self, queries: List[str], rag_chain):
        """缓存预热 - 提前计算热门查询"""
        logger.info(f"开始缓存预热: {len(queries)} 个查询")

        for query in queries:
            # 只预热未缓存的查询
            cached = await self.get(query)
            if cached is None:
                logger.debug(f"预热查询: {query[:30]}...")
                try:
                    result = rag_chain.run(query, top_k=3, use_rag=True)
                    await self.set(query, result, ttl=self.LONG_TTL)
                except Exception as e:
                    logger.error(f"预热失败: {query[:30]} - {e}")

        logger.info("缓存预热完成")


# 全局缓存管理器实例
cache_manager = CacheManager()
