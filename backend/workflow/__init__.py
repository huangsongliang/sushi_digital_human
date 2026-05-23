"""Workflow 引擎模块

提供流程定义、执行引擎和版本管理功能。

核心组件：
- WorkflowDefinition: 流程定义模型
- WorkflowEngine: 流程执行引擎
- WorkflowVersionManager: 版本管理
- Node types: 各种流程节点类型

导出：
- 流程节点类型
- 流程定义类
- 流程引擎
- 版本管理器
"""

from backend.workflow.definition import (
    NodeType,
    WorkflowNode,
    StartNode,
    EndNode,
    TaskNode,
    ConditionNode,
    ParallelNode,
    LoopNode,
    WorkflowDefinition,
    WorkflowValidator,
    WorkflowParser,
)
from backend.workflow.engine import (
    WorkflowEngine,
    WorkflowContext,
    WorkflowStatus,
    ExecutionResult,
)
from backend.workflow.version_manager import WorkflowVersionManager

__all__ = [
    # 节点类型枚举
    "NodeType",
    # 节点类
    "WorkflowNode",
    "StartNode",
    "EndNode",
    "TaskNode",
    "ConditionNode",
    "ParallelNode",
    "LoopNode",
    # 流程定义
    "WorkflowDefinition",
    "WorkflowValidator",
    "WorkflowParser",
    # 流程引擎
    "WorkflowEngine",
    "WorkflowContext",
    "WorkflowStatus",
    "ExecutionResult",
    # 版本管理
    "WorkflowVersionManager",
]
