"""请求批处理模块 - 优化 API 调用效率
功能：
1. 批量收集相似请求
2. 合并处理减少 API 调用
3. 支持去重和缓存
"""
import asyncio
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class BatchRequest:
    """单个批处理请求"""
    
    def __init__(self, id: str, func: Callable, args: tuple, kwargs: dict):
        self.id = id
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.future = asyncio.Future()
        self.timestamp = datetime.now()


class RequestBatcher:
    """请求批处理器"""
    
    def __init__(
        self,
        batch_size: int = 10,
        timeout_ms: int = 500,
        max_batch_wait_ms: int = 2000
    ):
        """
        Args:
            batch_size: 最大批处理大小
            timeout_ms: 等待新请求的超时时间（毫秒）
            max_batch_wait_ms: 最大等待时间（毫秒）
        """
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self.max_batch_wait_ms = max_batch_wait_ms
        
        # 待处理的请求队列（按函数分组）
        self._pending_requests: Dict[str, List[BatchRequest]] = {}
        
        # 正在运行的批处理任务
        self._active_batches: Dict[str, asyncio.Task] = {}
        
        # 去重缓存（近期已处理的请求）
        self._dedupe_cache: Dict[str, Any] = {}
        self._dedupe_cache_max_size = 1000
        
        # 锁
        self._lock = asyncio.Lock()
    
    def _generate_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """生成请求的唯一标识（用于去重）"""
        func_name = getattr(func, '__name__', str(func))
        data = json.dumps({
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }, sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()
    
    def _generate_group_key(self, func: Callable) -> str:
        """生成批处理组的标识"""
        return getattr(func, '__name__', str(func))
    
    async def _process_batch(self, group_key: str):
        """处理一批请求"""
        try:
            async with self._lock:
                if group_key not in self._pending_requests:
                    return
                requests = self._pending_requests.pop(group_key)
            
            if not requests:
                return
            
            logger.debug(f"Processing batch for {group_key}: {len(requests)} requests")
            
            # 如果只有一个请求，直接处理
            if len(requests) == 1:
                req = requests[0]
                try:
                    result = await req.func(*req.args, **req.kwargs)
                    req.future.set_result(result)
                    
                    # 更新去重缓存
                    self._update_dedupe_cache(req.id, result)
                except Exception as e:
                    req.future.set_exception(e)
                return
            
            # 尝试批量处理
            try:
                # 检查函数是否支持批量处理
                if hasattr(requests[0].func, 'batch_handler'):
                    # 使用批量处理器
                    results = await requests[0].func.batch_handler(requests)
                    
                    for req, result in zip(requests, results):
                        if isinstance(result, Exception):
                            req.future.set_exception(result)
                        else:
                            req.future.set_result(result)
                            self._update_dedupe_cache(req.id, result)
                else:
                    # 并发处理多个请求
                    tasks = [req.func(*req.args, **req.kwargs) for req in requests]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for req, result in zip(requests, results):
                        if isinstance(result, Exception):
                            req.future.set_exception(result)
                        else:
                            req.future.set_result(result)
                            self._update_dedupe_cache(req.id, result)
            
            except Exception as e:
                # 批量处理失败，逐个处理
                logger.warning(f"Batch processing failed, falling back to individual: {e}")
                for req in requests:
                    try:
                        result = await req.func(*req.args, **req.kwargs)
                        req.future.set_result(result)
                        self._update_dedupe_cache(req.id, result)
                    except Exception as ex:
                        req.future.set_exception(ex)
        
        finally:
            # 清理批处理任务记录
            if group_key in self._active_batches:
                del self._active_batches[group_key]
    
    def _update_dedupe_cache(self, key: str, value: Any):
        """更新去重缓存"""
        if len(self._dedupe_cache) >= self._dedupe_cache_max_size:
            # 删除最旧的条目
            oldest_key = next(iter(self._dedupe_cache))
            del self._dedupe_cache[oldest_key]
        self._dedupe_cache[key] = value
    
    async def submit(
        self,
        func: Callable[..., Any],
        *args,
        dedupe: bool = True,
        **kwargs
    ) -> Any:
        """提交请求到批处理器"""
        request_key = self._generate_key(func, args, kwargs)
        group_key = self._generate_group_key(func)
        
        # 检查去重缓存
        if dedupe and request_key in self._dedupe_cache:
            return self._dedupe_cache[request_key]
        
        # 创建请求对象
        request = BatchRequest(
            id=request_key,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        async with self._lock:
            # 添加到待处理队列
            if group_key not in self._pending_requests:
                self._pending_requests[group_key] = []
            self._pending_requests[group_key].append(request)
            
            # 检查是否需要启动批处理
            should_start = False
            
            # 达到批处理大小
            if len(self._pending_requests[group_key]) >= self.batch_size:
                should_start = True
            # 首次请求，启动定时任务
            elif len(self._pending_requests[group_key]) == 1:
                should_start = True
        
        if should_start:
            # 启动批处理任务（带延迟）
            async def delayed_process():
                # 等待更多请求
                await asyncio.sleep(self.timeout_ms / 1000)
                
                # 检查是否需要处理
                async with self._lock:
                    if group_key not in self._pending_requests:
                        return
                    if len(self._pending_requests[group_key]) == 0:
                        return
                
                # 执行批处理
                await self._process_batch(group_key)
            
            # 如果已经有批处理任务在运行，不需要重复启动
            if group_key not in self._active_batches:
                task = asyncio.create_task(delayed_process())
                self._active_batches[group_key] = task
        
        # 等待结果
        return await request.future
    
    def get_stats(self) -> Dict[str, Any]:
        """获取批处理统计信息"""
        pending_count = sum(len(reqs) for reqs in self._pending_requests.values())
        return {
            "pending_requests": pending_count,
            "active_batches": len(self._active_batches),
            "dedupe_cache_size": len(self._dedupe_cache),
            "batch_size": self.batch_size,
            "timeout_ms": self.timeout_ms
        }


class SimilarQueryDeduplicator:
    """相似查询去重器"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: 相似度阈值（0-1），高于此值视为相似查询
        """
        self.similarity_threshold = similarity_threshold
        self._recent_queries: List[Tuple[str, str, datetime]] = []  # (query_hash, result, timestamp)
        self._max_history = 100
    
    def _jaccard_similarity(self, str1: str, str2: str) -> float:
        """计算 Jaccard 相似度"""
        set1 = set(str1.lower().split())
        set2 = set(str2.lower().split())
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union
    
    async def check_and_dedupe(
        self,
        query: str,
        handler: Callable[[str], Any]
    ) -> Any:
        """检查是否有相似查询，并返回结果"""
        now = datetime.now()
        
        # 清理过期记录（保留最近 5 分钟）
        self._recent_queries = [
            q for q in self._recent_queries
            if (now - q[2]).total_seconds() < 300
        ]
        
        # 检查相似查询
        for stored_query, result, _ in self._recent_queries:
            similarity = self._jaccard_similarity(query, stored_query)
            if similarity >= self.similarity_threshold:
                logger.debug(f"Similar query detected: '{query}' -> '{stored_query}'")
                return result
        
        # 执行查询
        result = await handler(query)
        
        # 记录查询
        if len(self._recent_queries) >= self._max_history:
            self._recent_queries.pop(0)
        self._recent_queries.append((query, result, now))
        
        return result
    
    def clear(self):
        """清空历史记录"""
        self._recent_queries.clear()


# 全局实例
request_batcher = RequestBatcher(batch_size=10, timeout_ms=500)
query_deduplicator = SimilarQueryDeduplicator(similarity_threshold=0.85)