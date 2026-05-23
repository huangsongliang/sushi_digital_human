"""
RAG 查询缓存模块
为 RAG 检索添加缓存，减少重复查询
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.memory.cache import cache_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RAGQueryCache:
    """RAG 查询缓存"""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: 缓存有效期（秒），默认1小时
        """
        self.ttl_seconds = ttl_seconds
        self._cache_hits = 0
        self._cache_misses = 0

    def _generate_cache_key(self, query: str, top_k: int, use_bm25: bool, use_vector: bool, use_rerank: bool) -> str:
        """生成缓存键"""
        key_data = {
            "query": query,
            "top_k": top_k,
            "use_bm25": use_bm25,
            "use_vector": use_vector,
            "use_rerank": use_rerank,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"rag_query:{hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()}"

    async def get(
        self, query: str, top_k: int, use_bm25: bool, use_vector: bool, use_rerank: bool
    ) -> Optional[List[Dict]]:
        """获取缓存的检索结果"""
        cache_key = self._generate_cache_key(query, top_k, use_bm25, use_vector, use_rerank)

        try:
            cached = await cache_manager.get(cache_key)
            if cached:
                self._cache_hits += 1
                logger.debug(f"RAG缓存命中: {query[:50]}...")
                return cached
        except Exception as e:
            logger.warning(f"读取RAG缓存失败: {str(e)}")

        self._cache_misses += 1
        return None

    async def set(
        self, query: str, top_k: int, use_bm25: bool, use_vector: bool, use_rerank: bool, results: List[Dict]
    ):
        """设置缓存的检索结果"""
        cache_key = self._generate_cache_key(query, top_k, use_bm25, use_vector, use_rerank)

        try:
            await cache_manager.set(cache_key, results, ttl=self.ttl_seconds)
            logger.debug(f"RAG缓存已保存: {query[:50]}...")
        except Exception as e:
            logger.warning(f"保存RAG缓存失败: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
        }

    def reset_stats(self):
        """重置统计"""
        self._cache_hits = 0
        self._cache_misses = 0


# 全局缓存实例
_rag_cache = RAGQueryCache(ttl_seconds=3600)


def get_rag_cache() -> RAGQueryCache:
    """获取RAG缓存实例"""
    return _rag_cache
