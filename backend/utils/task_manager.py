"""
轻量级异步任务管理器
支持内存存储或 Redis 存储（多 worker 共享）
支持高并发场景
"""

import threading
import uuid
import time
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import os
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """任务对象"""
    task_id: str
    func_name: str
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0
    
    @property
    def duration(self) -> float:
        if self.completed_at > 0:
            return self.completed_at - self.created_at
        return time.time() - self.created_at
    
    @property
    def is_complete(self) -> bool:
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "func_name": self.func_name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        task = cls(
            task_id=data['task_id'],
            func_name=data['func_name'],
            args=tuple(data.get('args', ())),
            kwargs=data.get('kwargs', {}),
            status=TaskStatus(data['status']),
            result=data.get('result'),
            error=data.get('error', ''),
            created_at=data['created_at'],
            started_at=data.get('started_at', 0),
            completed_at=data.get('completed_at', 0)
        )
        return task


class TaskStorage:
    """任务存储基类"""
    def get(self, task_id: str) -> Optional[Task]:
        raise NotImplementedError
    
    def set(self, task: Task):
        raise NotImplementedError
    
    def delete(self, task_id: str):
        raise NotImplementedError


class MemoryTaskStorage(TaskStorage):
    """内存存储（单 worker 用）"""
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.lock = threading.RLock()
    
    def get(self, task_id: str) -> Optional[Task]:
        with self.lock:
            return self.tasks.get(task_id)
    
    def set(self, task: Task):
        with self.lock:
            self.tasks[task.task_id] = task
    
    def delete(self, task_id: str):
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]


class RedisTaskStorage(TaskStorage):
    """Redis 存储（多 worker 共享用）"""
    def __init__(self):
        import redis
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        self.ttl = 7200  # 2小时过期
    
    def get(self, task_id: str) -> Optional[Task]:
        key = f"task:{task_id}"
        data = self.redis.get(key)
        if data:
            return Task.from_dict(json.loads(data))
        return None
    
    def set(self, task: Task):
        key = f"task:{task.task_id}"
        data = json.dumps(task.to_dict())
        self.redis.setex(key, self.ttl, data)
    
    def delete(self, task_id: str):
        key = f"task:{task_id}"
        self.redis.delete(key)


class TaskManager:
    """任务管理器"""
    
    def __init__(self, max_workers: int = 20):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_lock = threading.RLock()
        self.functions: Dict[str, Callable] = {}
        self._running = True
        self.storage: Union[RedisTaskStorage, MemoryTaskStorage]
        
        # 选择存储方式
        use_redis = os.getenv('USE_REDIS_STORAGE', 'false').lower() == 'true'
        if use_redis:
            try:
                self.storage = RedisTaskStorage()
                logger.info("使用 Redis 存储任务")
            except Exception as e:
                logger.warning(f"Redis 连接失败，回退到内存存储: {e}")
                self.storage = MemoryTaskStorage()
        else:
            self.storage = MemoryTaskStorage()
            logger.info("使用内存存储任务")
        
        # 注册函数
        self._register_functions()
        
        logger.info(f"TaskManager 已初始化，工作线程数: {max_workers}")
    
    def _register_functions(self):
        """注册可执行的函数"""
        from backend.chain import get_rag_chain
        from backend.memory import ConversationMemory
        import asyncio
        
        async def async_process_chat(query: str, session_id: str, top_k: int = 3, user_id: Optional[str] = None) -> dict:
            """处理聊天请求（异步版本）"""
            try:
                # 获取对话记忆
                memory = ConversationMemory(session_id)
                
                # 获取历史消息（最近20条）
                history = await memory.get_history(limit=20)
                
                # 构建上下文
                context = "\n".join([f"{msg.role}: {msg.content}" for msg in history])
                
                rag_chain = get_rag_chain()
                result = await rag_chain.async_run(
                    query=query,
                    top_k=top_k,
                    use_rag=True,
                    history=context
                )
                
                # 保存对话到记忆
                await memory.save_message("user", query)
                await memory.save_message("assistant", result.get('answer', ''))
                
                sources = []
                for ref in result.get('references', []):
                    if ref.get('metadata') and ref['metadata'].get('source'):
                        sources.append(ref['metadata']['source'])
                
                return {
                    "status": "success",
                    "answer": result.get('answer', ''),
                    "references": result.get('references', []),
                    "sources": sources
                }
                
            except Exception as e:
                logger.error(f"async_process_chat 失败: {e}")
                raise
        
        def process_chat(query: str, session_id: str, top_k: int = 3, user_id: Optional[str] = None) -> dict:
            """处理聊天请求（同步包装）"""
            return asyncio.run(async_process_chat(query, session_id, top_k, user_id))
        
        # 注册
        self.functions['process_chat'] = process_chat
    
    def submit(self, func_name: str, *args, **kwargs) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            func_name=func_name,
            args=args,
            kwargs=kwargs
        )
        
        self.storage.set(task)
        
        # 异步执行
        self.executor.submit(self._execute_task, task_id)
        
        logger.debug(f"任务已提交: {task_id} -> {func_name}")
        return task_id
    
    def _execute_task(self, task_id: str):
        """执行任务（Worker 线程）"""
        task = self.storage.get(task_id)
        if not task:
            return
        
        try:
            # 更新状态
            task.status = TaskStatus.PROCESSING
            task.started_at = time.time()
            self.storage.set(task)
            
            # 获取函数
            func = self.functions.get(task.func_name)
            if not func:
                raise ValueError(f"函数未注册: {task.func_name}")
            
            # 执行
            result = func(*task.args, **task.kwargs)
            
            # 更新结果
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self.storage.set(task)
            
            logger.debug(f"任务完成: {task_id}, 耗时 {task.duration:.2f}秒")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self.storage.set(task)
            logger.error(f"任务失败: {task_id}, 错误: {e}")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.storage.get(task_id)
    
    def cleanup_old_tasks(self, max_age: float = 3600.0):
        """清理旧任务（内存存储时）"""
        if isinstance(self.storage, MemoryTaskStorage):
            with self.task_lock:
                now = time.time()
                # Redis 自动过期，不需要手动清理
                pass
    
    def shutdown(self):
        """关闭"""
        self._running = False
        self.executor.shutdown(wait=False)
        logger.info("TaskManager 已关闭")


# ==================== 全局实例 ====================
_task_manager: Optional[TaskManager] = None

def get_task_manager() -> TaskManager:
    """获取任务管理器单例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(max_workers=20)
    return _task_manager

def init_task_manager():
    """初始化任务管理器"""
    get_task_manager()
