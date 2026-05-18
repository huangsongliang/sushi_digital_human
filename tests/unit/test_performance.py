"""性能优化模块单元测试"""
import pytest
import asyncio
import time
from backend.memory.multi_level_cache import LRUCache, MultiLevelCache
from backend.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError
from backend.utils.rate_limiter import TokenBucket, RedisTokenBucket
from backend.utils.request_batcher import RequestBatcher, SimilarQueryDeduplicator


class TestLRUCache:
    """LRU 缓存测试"""
    
    def test_cache_set_get(self):
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_eviction(self):
        cache = LRUCache(maxsize=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # 应该淘汰 key1
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_ttl(self):
        cache = LRUCache(maxsize=10, ttl_seconds=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_cache_stats(self):
        cache = LRUCache(maxsize=10)
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.stats
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert stats["hit_rate"] == 50.0


class TestCircuitBreaker:
    """熔断器测试"""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_normal(self):
        breaker = CircuitBreaker(name="test", failure_threshold=3, reset_timeout=1)
        
        async def success_func():
            return "success"
        
        result = await breaker.call(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_tripping(self):
        breaker = CircuitBreaker(name="test", failure_threshold=2, reset_timeout=1)
        
        async def fail_func():
            raise Exception("test failure")
        
        # 第一次失败
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        
        # 第二次失败 - 触发熔断
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        
        # 第三次调用应该触发熔断器
        with pytest.raises(CircuitBreakerError):
            await breaker.call(fail_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self):
        breaker = CircuitBreaker(name="test", failure_threshold=2, success_threshold=1, reset_timeout=0.5)
        
        async def fail_func():
            raise Exception("test failure")
        
        async def success_func():
            return "success"
        
        # 触发熔断
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        
        # 等待熔断重置
        await asyncio.sleep(0.6)
        
        # 恢复成功
        result = await breaker.call(success_func)
        assert result == "success"


class TestTokenBucket:
    """令牌桶测试"""
    
    def test_token_bucket_acquire(self):
        bucket = TokenBucket(capacity=5, refill_rate=1)
        assert bucket.try_acquire() is True
        assert bucket.try_acquire() is True
        assert bucket.try_acquire() is True
        assert bucket.try_acquire() is True
        assert bucket.try_acquire() is True
        
        # 桶空了
        assert bucket.try_acquire() is False
    
    def test_token_bucket_refill(self):
        bucket = TokenBucket(capacity=2, refill_rate=1)
        
        # 消耗所有令牌
        bucket.try_acquire()
        bucket.try_acquire()
        
        # 等待补充
        time.sleep(1.1)
        
        # 应该有一个令牌
        assert bucket.try_acquire() is True
        assert bucket.try_acquire() is False


class TestRequestBatcher:
    """请求批处理测试"""
    
    @pytest.mark.asyncio
    async def test_batcher_single_request(self):
        batcher = RequestBatcher(batch_size=5, timeout_ms=10)
        
        async def handler(x):
            return x * 2
        
        result = await batcher.submit(handler, 5)
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_batcher_dedupe(self):
        batcher = RequestBatcher(batch_size=5, timeout_ms=10)
        call_count = [0]
        
        async def handler(x):
            call_count[0] += 1
            return x * 2
        
        # 相同参数的请求应该去重
        result1 = await batcher.submit(handler, 5)
        result2 = await batcher.submit(handler, 5)
        
        assert result1 == 10
        assert result2 == 10
        assert call_count[0] == 1


class TestSimilarQueryDeduplicator:
    """相似查询去重测试"""
    
    @pytest.mark.asyncio
    async def test_deduplicator_exact_match(self):
        deduplicator = SimilarQueryDeduplicator(similarity_threshold=0.8)
        call_count = [0]
        
        async def handler(query):
            call_count[0] += 1
            return f"result for {query}"
        
        result1 = await deduplicator.check_and_dedupe("hello world", handler)
        result2 = await deduplicator.check_and_dedupe("hello world", handler)
        
        assert result1 == "result for hello world"
        assert result2 == "result for hello world"
        assert call_count[0] == 1
    
    @pytest.mark.asyncio
    async def test_deduplicator_similar_match(self):
        deduplicator = SimilarQueryDeduplicator(similarity_threshold=0.7)
        call_count = [0]
        
        async def handler(query):
            call_count[0] += 1
            return f"result for {query}"
        
        result1 = await deduplicator.check_and_dedupe("how are you", handler)
        result2 = await deduplicator.check_and_dedupe("how are you doing", handler)
        
        assert call_count[0] == 1  # 应该被认为是相似查询
    
    @pytest.mark.asyncio
    async def test_deduplicator_different_queries(self):
        deduplicator = SimilarQueryDeduplicator(similarity_threshold=0.8)
        call_count = [0]
        
        async def handler(query):
            call_count[0] += 1
            return f"result for {query}"
        
        result1 = await deduplicator.check_and_dedupe("hello world", handler)
        result2 = await deduplicator.check_and_dedupe("goodbye world", handler)
        
        assert call_count[0] == 2  # 应该被认为是不同查询