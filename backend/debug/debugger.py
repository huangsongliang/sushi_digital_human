"""调试器核心模块 - 提供调试上下文管理和执行控制功能"""

import asyncio
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutionState(str, Enum):
    """执行状态枚举"""

    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class StepMode(str, Enum):
    """单步执行模式"""

    STEP_INTO = "step_into"
    STEP_OVER = "step_over"
    STEP_OUT = "step_out"


class DebugContext:
    """调试上下文 - 存储单个执行的调试状态"""

    def __init__(self, execution_id: Optional[str] = None):
        self.execution_id = execution_id or str(uuid.uuid4())
        self.state = ExecutionState.STOPPED
        self.current_step = 0
        self.variables: Dict[str, Any] = {}
        self.call_stack: list = []
        self.pause_event = asyncio.Event()
        self.resume_event = asyncio.Event()
        self.step_mode: Optional[StepMode] = None

    async def pause(self):
        """暂停执行"""
        if self.state == ExecutionState.RUNNING:
            self.state = ExecutionState.PAUSED
            self.pause_event.set()
            logger.debug(f"Execution {self.execution_id} paused")

    async def resume(self):
        """恢复执行"""
        if self.state == ExecutionState.PAUSED:
            self.state = ExecutionState.RUNNING
            self.resume_event.set()
            self.pause_event.clear()
            logger.debug(f"Execution {self.execution_id} resumed")

    async def wait_for_resume(self):
        """等待恢复信号"""
        if self.state == ExecutionState.PAUSED:
            await self.resume_event.wait()
            self.resume_event.clear()

    async def step(self, mode: StepMode = StepMode.STEP_OVER):
        """执行单步操作"""
        self.step_mode = mode
        await self.resume()

    def set_variable(self, name: str, value: Any):
        """设置调试变量"""
        self.variables[name] = value

    def get_variable(self, name: str) -> Optional[Any]:
        """获取调试变量"""
        return self.variables.get(name)

    def push_stack_frame(self, frame_info: Dict[str, Any]):
        """推入调用栈帧"""
        self.call_stack.append(frame_info)

    def pop_stack_frame(self) -> Optional[Dict[str, Any]]:
        """弹出调用栈帧"""
        return self.call_stack.pop() if self.call_stack else None

    def clear(self):
        """清除上下文"""
        self.state = ExecutionState.STOPPED
        self.current_step = 0
        self.variables.clear()
        self.call_stack.clear()
        self.pause_event.clear()
        self.resume_event.clear()


class Debugger:
    """调试器 - 管理多个执行的调试状态"""

    def __init__(self):
        self.contexts: Dict[str, DebugContext] = {}
        self._lock = asyncio.Lock()

    async def create_context(self, execution_id: Optional[str] = None) -> DebugContext:
        """创建新的调试上下文"""
        async with self._lock:
            ctx = DebugContext(execution_id)
            self.contexts[ctx.execution_id] = ctx
            logger.debug(f"Created debug context: {ctx.execution_id}")
            return ctx

    async def get_context(self, execution_id: str) -> Optional[DebugContext]:
        """获取调试上下文"""
        async with self._lock:
            return self.contexts.get(execution_id)

    async def remove_context(self, execution_id: str):
        """移除调试上下文"""
        async with self._lock:
            ctx = self.contexts.pop(execution_id, None)
            if ctx:
                ctx.clear()
                logger.debug(f"Removed debug context: {execution_id}")

    async def pause_execution(self, execution_id: str) -> bool:
        """暂停指定执行"""
        ctx = await self.get_context(execution_id)
        if ctx and ctx.state == ExecutionState.RUNNING:
            await ctx.pause()
            return True
        return False

    async def resume_execution(self, execution_id: str) -> bool:
        """恢复指定执行"""
        ctx = await self.get_context(execution_id)
        if ctx and ctx.state == ExecutionState.PAUSED:
            await ctx.resume()
            return True
        return False

    async def step_execution(self, execution_id: str, mode: StepMode = StepMode.STEP_OVER) -> bool:
        """单步执行"""
        ctx = await self.get_context(execution_id)
        if ctx and ctx.state == ExecutionState.PAUSED:
            await ctx.step(mode)
            return True
        return False

    async def get_execution_state(self, execution_id: str) -> Optional[ExecutionState]:
        """获取执行状态"""
        ctx = await self.get_context(execution_id)
        return ctx.state if ctx else None

    async def update_step(self, execution_id: str, step: int):
        """更新当前步骤"""
        ctx = await self.get_context(execution_id)
        if ctx:
            ctx.current_step = step

    async def get_all_contexts(self) -> Dict[str, DebugContext]:
        """获取所有调试上下文"""
        async with self._lock:
            return dict(self.contexts)

    async def cleanup_completed(self):
        """清理已完成的执行上下文"""
        async with self._lock:
            completed_ids = [eid for eid, ctx in self.contexts.items() if ctx.state == ExecutionState.COMPLETED]
            for eid in completed_ids:
                ctx = self.contexts.pop(eid)
                ctx.clear()
                logger.debug(f"Cleaned up completed context: {eid}")


debugger = Debugger()
