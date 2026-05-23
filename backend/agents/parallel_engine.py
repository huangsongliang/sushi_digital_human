"""并行执行引擎模块

负责异步任务执行、结果聚合与合并、故障恢复机制。
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.utils.circuit_breaker import CircuitBreaker
from backend.utils.logger import get_logger

from .task_splitter import Task, TaskPriority, TaskStatus

logger = get_logger(__name__)


class ExecutionResult(BaseModel):
    """任务执行结果"""

    task_id: str = Field(..., description="任务ID")
    success: bool = Field(..., description="执行是否成功")
    result: Optional[Dict[str, Any]] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time_ms: float = Field(..., description="执行耗时（毫秒）")


class ParallelEngine:
    """并行任务执行引擎"""

    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        default_timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self._max_concurrent = max_concurrent_tasks
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        self._task_registry: Dict[str, Task] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def execute_tasks(
        self,
        tasks: List[Task],
        executor: Callable[[Task], Any],
        sequential: bool = False,
    ) -> List[ExecutionResult]:
        """执行任务列表

        Args:
            tasks: 任务列表
            executor: 任务执行器函数
            sequential: 是否串行执行（默认并行）

        Returns:
            执行结果列表
        """
        logger.info(f"开始执行任务，共 {len(tasks)} 个任务，模式: {'串行' if sequential else '并行'}")

        for task in tasks:
            self._task_registry[task.id] = task

        if sequential:
            return await self._execute_sequential(tasks, executor)
        else:
            return await self._execute_parallel(tasks, executor)

    async def _execute_sequential(
        self,
        tasks: List[Task],
        executor: Callable[[Task], Any],
    ) -> List[ExecutionResult]:
        """串行执行任务"""
        results = []

        for task in tasks:
            result = await self._execute_task_with_retry(task, executor)
            results.append(result)

            if not result.success:
                logger.warning(f"任务 {task.id} 执行失败，后续任务可能受影响")

        return results

    async def _execute_parallel(
        self,
        tasks: List[Task],
        executor: Callable[[Task], Any],
    ) -> List[ExecutionResult]:
        """并行执行任务"""
        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def bounded_executor(task: Task) -> ExecutionResult:
            async with semaphore:
                return await self._execute_task_with_retry(task, executor)

        tasks_map = {task.id: task for task in tasks}
        dependencies_map = self._build_dependency_map(tasks)

        all_results = {}
        completed = set()
        remaining = set(tasks)

        while remaining:
            executable = [
                task for task in remaining if all(dep in completed for dep in dependencies_map.get(task.id, []))
            ]

            if not executable:
                logger.warning("无法继续执行，可能存在循环依赖")
                break

            logger.debug(f"并行执行 {len(executable)} 个任务")

            coroutines = [bounded_executor(task) for task in executable]
            batch_results = await asyncio.gather(*coroutines)

            for result in batch_results:
                all_results[result.task_id] = result
                completed.add(result.task_id)
                remaining.discard(tasks_map[result.task_id])

        return list(all_results.values())

    def _build_dependency_map(self, tasks: List[Task]) -> Dict[str, Set[str]]:
        """构建任务依赖映射"""
        dependency_map: Dict[str, Set[str]] = {}
        task_ids = {t.id for t in tasks}

        for task in tasks:
            deps = set()
            for dep in task.dependencies:
                if dep.task_id in task_ids:
                    deps.add(dep.task_id)
            dependency_map[task.id] = deps

        return dependency_map

    async def _execute_task_with_retry(
        self,
        task: Task,
        executor: Callable[[Task], Any],
    ) -> ExecutionResult:
        """带重试机制执行单个任务"""
        start_time = time.time()

        for attempt in range(self._max_retries + 1):
            try:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()

                logger.debug(f"执行任务 {task.id} (尝试 {attempt + 1}/{self._max_retries + 1})")

                result = await asyncio.wait_for(
                    executor(task),
                    timeout=self._default_timeout,
                )

                execution_time = (time.time() - start_time) * 1000

                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.progress = 1.0
                task.result = result

                logger.info(f"任务 {task.id} 执行成功，耗时 {execution_time:.2f}ms")

                return ExecutionResult(
                    task_id=task.id,
                    success=True,
                    result=result,
                    execution_time_ms=execution_time,
                )

            except asyncio.TimeoutError:
                error_msg = f"任务 {task.id} 超时"
                logger.warning(f"{error_msg} (尝试 {attempt + 1})")

                if attempt >= self._max_retries:
                    task.status = TaskStatus.FAILED
                    task.error = error_msg
                    return ExecutionResult(
                        task_id=task.id,
                        success=False,
                        error=error_msg,
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )

            except Exception as e:
                error_msg = f"任务 {task.id} 执行异常: {str(e)}"
                logger.error(f"{error_msg} (尝试 {attempt + 1})")

                if attempt >= self._max_retries:
                    task.status = TaskStatus.FAILED
                    task.error = error_msg
                    return ExecutionResult(
                        task_id=task.id,
                        success=False,
                        error=error_msg,
                        execution_time_ms=(time.time() - start_time) * 1000,
                    )

            await asyncio.sleep(2**attempt)

        task.status = TaskStatus.FAILED
        return ExecutionResult(
            task_id=task.id,
            success=False,
            error="未知错误",
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    def aggregate_results(self, results: List[ExecutionResult]) -> Dict[str, Any]:
        """聚合多个任务的执行结果

        Args:
            results: 执行结果列表

        Returns:
            聚合后的结果
        """
        aggregated = {
            "success_count": 0,
            "failed_count": 0,
            "total_execution_time_ms": 0.0,
            "results": {},
            "errors": {},
        }

        for result in results:
            aggregated["total_execution_time_ms"] += result.execution_time_ms

            if result.success:
                aggregated["success_count"] += 1
                aggregated["results"][result.task_id] = result.result
            else:
                aggregated["failed_count"] += 1
                aggregated["errors"][result.task_id] = result.error

        return aggregated

    def merge_results(self, results: List[ExecutionResult], merge_strategy: str = "concat") -> Any:
        """合并多个任务结果为统一输出

        Args:
            results: 执行结果列表
            merge_strategy: 合并策略 (concat, first, last, merge_dict)

        Returns:
            合并后的结果
        """
        successful_results = [r for r in results if r.success and r.result]

        if not successful_results:
            return None

        if merge_strategy == "first":
            return successful_results[0].result

        elif merge_strategy == "last":
            return successful_results[-1].result

        elif merge_strategy == "concat":
            if all(isinstance(r.result, str) for r in successful_results):
                return "\n\n".join(r.result for r in successful_results)
            elif all(isinstance(r.result, list) for r in successful_results):
                return [item for r in successful_results for item in r.result]
            else:
                return [r.result for r in successful_results]

        elif merge_strategy == "merge_dict":
            merged = {}
            for r in successful_results:
                if isinstance(r.result, dict):
                    merged.update(r.result)
            return merged

        else:
            return [r.result for r in successful_results]

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态，如果任务不存在返回None
        """
        task = self._task_registry.get(task_id)
        return task.status if task else None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功取消
        """
        task = self._task_registry.get(task_id)
        if task and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            logger.info(f"任务 {task_id} 已取消")
            return True
        return False

    def get_task_summary(self) -> Dict[str, Any]:
        """获取任务执行摘要"""
        status_counts = {status.value: 0 for status in TaskStatus}

        for task in self._task_registry.values():
            status_counts[task.status.value] += 1

        return {
            "total_tasks": len(self._task_registry),
            **status_counts,
        }


# 全局并行引擎实例
parallel_engine = ParallelEngine()
