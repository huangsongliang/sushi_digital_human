"""限流模块 - 防止 API 滥用（性能优化版）"""
from typing import Callable, Dict, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Request, status
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class RateLimiter:
    """Redis 限流器 - 支持多级别限流"""
    
    def __init__(self):
        """
        初始化限流器
        """
        # 限流级别配置（宽松配置，适合高并发）
        self.policies = {
            "chat": {
                "max_requests": 5000,
                "window_seconds": 60,
                "burst_limit": 1000
            },
            "stream": {
                "max_requests": 2000,
                "window_seconds": 60,
                "burst_limit": 500
            },
            "docs": {
                "max_requests": 1000,
                "window_seconds": 60,
                "burst_limit": 200
            },
            "default": {
                "max_requests": 10000,
                "window_seconds": 60,
                "burst_limit": 2000
            }
        }
        self.prefix = "rate_limit:"
        self.burst_prefix = "burst_limit:"
    
    def _get_policy(self, endpoint: str) -> Dict:
        """获取限流策略"""
        if "/chat/stream" in endpoint:
            return self.policies["stream"]
        elif "/chat" in endpoint:
            return self.policies["chat"]
        elif "/docs" in endpoint:
            return self.policies["docs"]
        return self.policies["default"]
    
    async def check(self, client_id: str, endpoint: str) -> bool:
        """检查是否允许请求"""
        policy = self._get_policy(endpoint)
        
        try:
            client = await redis_conn.get_client()
            key = f"{self.prefix}{endpoint}:{client_id}"
            burst_key = f"{self.burst_prefix}{endpoint}:{client_id}"
            
            # 检查突发限制
            burst_current = await client.get(burst_key)
            burst_current = int(burst_current.decode('utf-8') if isinstance(burst_current, bytes) else burst_current) if burst_current else 0
            
            if burst_current >= policy["burst_limit"]:
                logger.warning(f"突发限流触发: {client_id}, 端点: {endpoint}")
                return False
            
            # 检查常规限制
            current = await client.get(key)
            
            if current is None:
                await client.setex(key, policy["window_seconds"], 1)
                await client.setex(burst_key, 10, 1)  # 10秒窗口的突发计数
                return True
            
            count = int(current.decode('utf-8') if isinstance(current, bytes) else current)
            if count >= policy["max_requests"]:
                ttl = await client.ttl(key)
                logger.warning(f"限流触发: {client_id}, 端点: {endpoint}, 剩余时间: {ttl}s")
                return False
            
            await client.incr(key)
            await client.incr(burst_key)
            
            return True
        
        except Exception as e:
            logger.error(f"限流检查失败: {e}")
            return True
    
    async def get_remaining(self, client_id: str, endpoint: str) -> Dict[str, int]:
        """获取剩余请求数和重置时间"""
        policy = self._get_policy(endpoint)
        
        try:
            client = await redis_conn.get_client()
            key = f"{self.prefix}{endpoint}:{client_id}"
            
            current = await client.get(key)
            ttl = await client.ttl(key)
            
            count = int(current.decode('utf-8') if isinstance(current, bytes) else current) if current else 0
            
            return {
                "remaining": max(0, policy["max_requests"] - count),
                "reset_in": ttl if ttl > 0 else policy["window_seconds"]
            }
        except Exception as e:
            logger.error(f"获取限流状态失败: {e}")
            return {"remaining": policy["max_requests"], "reset_in": policy["window_seconds"]}


class RequestQueue:
    """请求队列管理器 - 控制并发处理"""
    
    def __init__(self, max_concurrent: int = 200):
        """
        Args:
            max_concurrent: 最大并发请求数
        """
        self.max_concurrent = max_concurrent
        self.current_concurrent = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue = asyncio.Queue(maxsize=max_concurrent * 2)
        self._task_count = 0
        self._active_tasks = set()
    
    async def acquire(self) -> bool:
        """获取处理槽位"""
        try:
            await self._semaphore.acquire()
            self.current_concurrent += 1
            return True
        except asyncio.CancelledError:
            return False
    
    def release(self):
        """释放处理槽位"""
        self._semaphore.release()
        self.current_concurrent -= 1
    
    async def process_request(self, coro, *args, **kwargs):
        """处理请求（带队列管理）"""
        async with self._semaphore:
            self.current_concurrent += 1
            try:
                return await coro(*args, **kwargs)
            finally:
                self.current_concurrent -= 1
    
    def get_stats(self) -> Dict[str, int]:
        """获取队列统计"""
        return {
            "current_concurrent": self.current_concurrent,
            "max_concurrent": self.max_concurrent,
            "queue_size": self._queue.qsize(),
            "task_count": self._task_count
        }


# 全局实例
rate_limiter = RateLimiter()
request_queue = RequestQueue(max_concurrent=20)


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI 限流中间件"""
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    endpoint = request.url.path
    
    allowed = await rate_limiter.check(client_ip, endpoint)
    if not allowed:
        remaining_info = await rate_limiter.get_remaining(client_ip, endpoint)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Too many requests",
                "message": "请求过于频繁，请稍后重试",
                "remaining": remaining_info["remaining"],
                "reset_in": remaining_info["reset_in"],
                "endpoint": endpoint
            },
            headers={
                "Retry-After": str(remaining_info["reset_in"]),
                "X-RateLimit-Remaining": str(remaining_info["remaining"]),
                "X-RateLimit-Reset": str(remaining_info["reset_in"])
            }
        )
    
    remaining_info = await rate_limiter.get_remaining(client_ip, endpoint)
    
    response = await call_next(request)
    
    response.headers["X-RateLimit-Remaining"] = str(remaining_info["remaining"])
    response.headers["X-RateLimit-Limit"] = str(rate_limiter._get_policy(endpoint)["max_requests"])
    response.headers["X-RateLimit-Reset"] = str(remaining_info["reset_in"])
    
    return response


async def concurrency_limit_middleware(request: Request, call_next):
    """并发限制中间件"""
    async with request_queue._semaphore:
        return await call_next(request)
