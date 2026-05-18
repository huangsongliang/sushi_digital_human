"""缓存模块单元测试"""
import pytest
from unittest.mock import MagicMock, patch
from backend.memory.cache import CacheManager


class TestCacheManager:
    """缓存管理器测试"""
    
    def test_cache_manager_creation(self):
        with patch('backend.memory.cache.redis_conn'):
            cache = CacheManager()
            assert cache is not None
    
    def test_generate_key(self):
        key = CacheManager.generate_key("test", "query", use_rag=True)
        assert key is not None
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
    
    def test_generate_embedding_key(self):
        key = CacheManager.generate_embedding_key("test text")
        assert key is not None
        assert isinstance(key, str)
        assert len(key) == 32