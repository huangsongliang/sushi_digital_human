"""限流模块 - 防止 API 滥用（性能优化版）
支持多种限流算法：
1. 固定窗口计数器
2. 滑动窗口计数器
3. 令牌桶算法（推荐用于突发流量）
"""
import time
from typing import Dict, Set, Optional
from asyncio import Queue, Task
from fastapi import HTTPException, Request, status
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger
import asyncio

logger = get_logger(__name__)


class TokenBucket:
    """令牌桶算法实现 - 支持突发流量控制"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: 桶的容量（最大令牌数）
            refill_rate: 令牌填充速率（每秒填充的令牌数）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill_time = time.time()
    
    def _refill(self):
        """补充令牌"""
        now = time.time()
        time_passed = now - self.last_refill_time
        new_tokens = time_passed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill_time = now
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """尝试获取令牌"""
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_available_tokens(self) -> float:
        """获取当前可用令牌数"""
        self._refill()
        return self.tokens


class RedisTokenBucket:
    """基于 Redis 的分布式令牌桶"""
    
    def __init__(self):
        self.prefix = "token_bucket:"
        
    async def acquire(self, client_id: str, endpoint: str, tokens: int = 1) -> bool:
        """获取令牌"""
        policy = self._get_policy(endpoint)
        capacity = policy["burst_limit"]
        refill_rate = policy["max_requests"] / policy["window_seconds"]
        
        client = await redis_conn.get_client()
        key = f"{self.prefix}{endpoint}:{client_id}"
        
        # 使用 Lua 脚本实现原子操作
        lua_script = """
            local key = KEYS[1]
            local capacity = tonumber(ARGV[1])
            local refill_rate = tonumber(ARGV[2])
            local tokens_requested = tonumber(ARGV[3])
            
            -- 获取当前状态
            local current = redis.call('GET', key)
            if not current then
                -- 首次请求，初始化
                redis.call('SET', key, capacity - tokens_requested)
                redis.call('PEXPIRE', key, 60000)  -- 60秒过期
                return 1
            end
            
            -- 解析当前令牌数和时间戳
            local parts = {}
            for part in string.gmatch(current, '[^|]+') do
                table.insert(parts, part)
            end
            
            local tokens = tonumber(parts[1]) or capacity
            local last_time = tonumber(parts[2]) or tonumber(redis.call('TIME')[1])
            
            -- 计算时间差并补充令牌
            local now = tonumber(redis.call('TIME')[1])
            local time_passed = now - last_time
            local new_tokens = time_passed * refill_rate
            tokens = math.min(capacity, tokens + new_tokens)
            
            -- 检查是否有足够令牌
            if tokens >= tokens_requested then
                tokens = tokens - tokens_requested
                redis.call('SET', key, tokens .. '|' .. now)
                return 1
            else
                return 0
            end
        """
        
        try:
            result = await client.eval(
                lua_script,
                keys=[key],
                args=[capacity, refill_rate, tokens]
            )
            return result == 1
        except Exception as e:
            logger.error(f"Redis token bucket error: {e}")
            return True  # 降级允许请求
    
    def _get_policy(self, endpoint: str) -> Dict:
        """获取限流策略"""
        policies = {
            "chat": {"max_requests": 5000, "window_seconds": 60, "burst_limit": 1000},
            "stream": {"max_requests": 2000, "window_seconds": 60, "burst_limit": 500},
            "docs": {"max_requests": 1000, "window_seconds": 60, "burst_limit": 200},
            "default": {"max_requests": 10000, "window_seconds": 60, "burst_limit": 2000}
        }
        
        if "/chat/stream" in endpoint:
            return policies["stream"]
        elif "/chat" in endpoint:
            return policies["chat"]
        elif "/docs" in endpoint:
            return policies["docs"]
        return policies["default"]


class RateLimiter:
    """Redis 限流器 - 支持多级别限流"""

    def __init__(self):
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
        
        # 令牌桶实例
        self.token_bucket = RedisTokenBucket()

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
        """检查是否允许请求（使用令牌桶算法）"""
        return await self.token_bucket.acquire(client_id, endpoint)

    async def check_sliding_window(self, client_id: str, endpoint: str) -> bool:
        """检查是否允许请求（使用滑动窗口算法）"""
        policy = self._get_policy(endpoint)

        try:
            client = await redis_conn.get_client()
            key = f"{self.prefix}{endpoint}:{client_id}"
            window = policy["window_seconds"]
            max_requests = policy["max_requests"]
            
            # 使用 Redis sorted set 实现滑动窗口
            now = int(time.time())
            window_start = now - window
            
            # 删除窗口外的记录
            await client.zremrangebyscore(key, 0, window_start)
            
            # 获取窗口内的请求数
            count = await client.zcard(key)
            
            if count >= max_requests:
                logger.warning(f"限流触发: {client_id}, 端点: {endpoint}")
                return False
            
            # 添加当前请求时间戳
            await client.zadd(key, {now: now})
            await client.expire(key, window + 1)
            
            return True

        except Exception as e:
            logger.error(f"限流检查失败: {e}")
            return True

    async def get_remaining(
        self, client_id: str, endpoint: str
    ) -> Dict[str, int]:
        """获取剩余请求数和重置时间"""
        policy = self._get_policy(endpoint)

        try:
            client = await redis_conn.get_client()
            key = f"{self.prefix}{endpoint}:{client_id}"

            current = await client.get(key)
            ttl = await client.ttl(key)

            count = int(
                current.decode('utf-8')
                if isinstance(current, bytes)
                else current
            ) if current else 0

            return {
                "remaining": max(0, policy["max_requests"] - count),
                "reset_in": ttl if ttl > 0 else policy["window_seconds"]
            }
        except Exception as e:
            logger.error(f"获取限流状态失败: {e}")
            return {
                "remaining": policy["max_requests"],
                "reset_in": policy["window_seconds"]
            }


class RequestQueue:
    """请求队列管理器 - 控制并发处理"""

    def __init__(self, max_concurrent: int = 200):
        self.max_concurrent = max_concurrent
        self.current_concurrent = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: Queue = asyncio.Queue(maxsize=max_concurrent * 2)
        self._task_count = 0
        self._active_tasks: Set[Task] = set()

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
    client_host = request.client.host if request.client else "unknown"
    client_ip = request.headers.get("X-Forwarded-For", client_host)
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

    response.headers["X-RateLimit-Remaining"] = (
        str(remaining_info["remaining"])
    )
    response.headers["X-RateLimit-Limit"] = str(
        rate_limiter._get_policy(endpoint)["max_requests"]
    )
    response.headers["X-RateLimit-Reset"] = str(remaining_info["reset_in"])

    return response


async def concurrency_limit_middleware(request: Request, call_next):
    """并发限制中间件"""
    async with request_queue._semaphore:
        return await call_next(request)
