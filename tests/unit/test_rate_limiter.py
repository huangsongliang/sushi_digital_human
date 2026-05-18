"""限流模块单元测试"""
from backend.utils.rate_limiter import (
    RateLimiter,
    RequestQueue,
    rate_limiter,
    request_queue
)


class TestRateLimiter:
    """限流器测试"""

    def test_rate_limiter_creation(self):
        limiter = RateLimiter()
        assert limiter is not None
        assert "chat" in limiter.policies
        assert "default" in limiter.policies

    def test_rate_limiter_policies(self):
        limiter = RateLimiter()
        chat_policy = limiter._get_policy("/chat")
        assert chat_policy["max_requests"] == 5000
        stream_policy = limiter._get_policy("/chat/stream")
        assert stream_policy["max_requests"] == 2000


class TestRequestQueue:
    """请求队列测试"""

    def test_request_queue_creation(self):
        queue = RequestQueue(max_concurrent=10)
        assert queue is not None
        assert queue.max_concurrent == 10

    def test_acquire_release(self):
        queue = RequestQueue(max_concurrent=10)
        assert queue.acquire() is not None

    def test_get_stats(self):
        queue = RequestQueue(max_concurrent=10)
        stats = queue.get_stats()
        assert "current_concurrent" in stats
        assert "max_concurrent" in stats
        assert "queue_size" in stats


class TestGlobalInstances:
    """全局实例测试"""

    def test_rate_limiter_singleton(self):
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)

    def test_request_queue_singleton(self):
        assert request_queue is not None
        assert isinstance(request_queue, RequestQueue)
