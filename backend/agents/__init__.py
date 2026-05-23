"""多Agent协作框架

提供多Agent协作的核心能力，包括：
- 角色管理与分配
- 任务拆分与优先级排序
- 并行任务执行引擎
- Agent间消息传递机制

导出模块：
- AgentRole: Agent角色数据模型
- RoleManager: 角色管理类
- TaskSplitter: 任务拆分器
- ParallelEngine: 并行执行引擎
- MessageQueue: 消息队列系统
"""

from .role_manager import AgentRole, RoleManager
from .task_splitter import Task, TaskSplitter
from .parallel_engine import ParallelEngine
from .messaging import MessageQueue, AgentMessage

__all__ = [
    "AgentRole",
    "RoleManager",
    "Task",
    "TaskSplitter",
    "ParallelEngine",
    "MessageQueue",
    "AgentMessage",
]
