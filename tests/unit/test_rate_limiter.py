"""限流模块单元测试"""
import pytest
from backend.utils.rate_limiter import RateLimiter, RequestQueue, rate_limiter, request_queue


class TestRateLimiter:
    """限流器测试"""
    
    def test_rate_limiter_creation(self):
        limiter = RateLimiter()
        assert limiter is not None
        assert "chat" in limiter.policies
        assert "stream" in limiter.policies
        assert "docs" in limiter.policies
        assert "default" in limiter.policies
    
    def test_get_policy(self):
        limiter = RateLimiter()
        
        assert limiter._get_policy("/api/chat") == limiter.policies["chat"]
        assert limiter._get_policy("/api/chat/stream") == limiter.policies["stream"]
        assert limiter._get_policy("/api/docs/add") == limiter.policies["docs"]
        assert limiter._get_policy("/api/health") == limiter.policies["default"]
    
    def test_policy_structure(self):
        limiter = RateLimiter()
        policy = limiter.policies["chat"]
        
        assert "max_requests" in policy
        assert "window_seconds" in policy
        assert "burst_limit" in policy


class TestRequestQueue:
    """请求队列测试"""
    
    def test_request_queue_creation(self):
        queue = RequestQueue(max_concurrent=10)
        assert queue.max_concurrent == 10
        assert queue.current_concurrent == 0
    
    @pytest.mark.asyncio
    async def test_acquire_release(self):
        queue = RequestQueue(max_concurrent=2)
        
        result = await queue.acquire()
        assert result is True
        assert queue.current_concurrent == 1
        
        result = await queue.acquire()
        assert result is True
        assert queue.current_concurrent == 2
        
        queue.release()
        assert queue.current_concurrent == 1
        
        queue.release()
        assert queue.current_concurrent == 0
    
    def test_get_stats(self):
        queue = RequestQueue(max_concurrent=10)
        
        stats = queue.get_stats()
        assert "current_concurrent" in stats
        assert "max_concurrent" in stats
        assert "queue_size" in stats
        assert "task_count" in stats
        assert stats["max_concurrent"] == 10


class TestGlobalInstances:
    """全局实例测试"""
    
    def test_rate_limiter_instance(self):
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)
    
    def test_request_queue_instance(self):
        assert request_queue is not None
        assert isinstance(request_queue, RequestQueue)