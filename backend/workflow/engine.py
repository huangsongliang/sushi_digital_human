"""流程执行引擎模块

包含：
- 流程状态机
- 节点执行逻辑
- 流程上下文管理
"""

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field
from backend.utils.logger import get_logger
from backend.workflow.definition import (
    ConditionNode,
    EndNode,
    LoopNode,
    NodeType,
    ParallelNode,
    StartNode,
    TaskNode,
    WorkflowDefinition,
    WorkflowValidator,
)

logger = get_logger(__name__)


class WorkflowStatus(str, Enum):
    """流程状态枚举"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ExecutionResult(BaseModel):
    """执行结果模型"""

    workflow_id: str = Field(..., description="流程ID")
    execution_id: str = Field(..., description="执行ID")
    status: WorkflowStatus = Field(..., description="执行状态")
    output: Dict[str, Any] = Field(default_factory=dict, description="输出数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    started_at: str = Field(..., description="开始时间")
    completed_at: Optional[str] = Field(default=None, description="完成时间")
    node_executions: List[Dict[str, Any]] = Field(default_factory=list, description="节点执行记录")


class WorkflowContext:
    """流程上下文管理器"""

    def __init__(self, execution_id: str, input_data: Optional[Dict[str, Any]] = None):
        self.execution_id = execution_id
        self.data = input_data or {}
        self._history: List[Dict[str, Any]] = []
        self._started_at = time.time()
        self._completed_at: Optional[float] = None

    def set(self, key: str, value: Any):
        """设置上下文变量"""
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self.data.get(key, default)

    def update(self, data: Dict[str, Any]):
        """批量更新上下文"""
        self.data.update(data)

    def record_execution(self, node_id: str, node_type: NodeType, result: Any, error: Optional[str] = None):
        """记录节点执行记录"""
        self._history.append({
            "node_id": node_id,
            "node_type": node_type.value,
            "timestamp": time.time(),
            "result": result,
            "error": error,
        })

    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._history

    def mark_completed(self):
        """标记完成"""
        self._completed_at = time.time()

    @property
    def started_at(self) -> float:
        """开始时间戳"""
        return self._started_at

    @property
    def completed_at(self) -> Optional[float]:
        """完成时间戳"""
        return self._completed_at


class WorkflowEngine:
    """流程执行引擎"""

    def __init__(self):
        self._executions: Dict[str, WorkflowContext] = {}
        self._running_workflows: Set[str] = set()

    async def execute(self, definition: WorkflowDefinition, input_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """执行流程

        Args:
            definition: 流程定义
            input_data: 输入数据

        Returns:
            执行结果
        """
        from uuid import uuid4

        execution_id = str(uuid4())

        if not WorkflowValidator.is_valid(definition):
            errors = WorkflowValidator.validate(definition)
            return ExecutionResult(
                workflow_id=definition.id,
                execution_id=execution_id,
                status=WorkflowStatus.FAILED,
                error=f"流程定义无效: {'; '.join(errors)}",
                started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )

        context = WorkflowContext(execution_id, input_data)
        self._executions[execution_id] = context
        self._running_workflows.add(execution_id)

        logger.info(f"开始执行流程: {definition.id}, 执行ID: {execution_id}")

        try:
            await self._execute_node(definition, context, definition.start_node_id)
            status = WorkflowStatus.COMPLETED
            error = None
        except Exception as e:
            logger.error(f"流程执行失败: {str(e)}", exc_info=True)
            status = WorkflowStatus.FAILED
            error = str(e)
        finally:
            context.mark_completed()
            self._running_workflows.discard(execution_id)

        logger.info(f"流程执行完成: {definition.id}, 执行ID: {execution_id}, 状态: {status.value}")

        return ExecutionResult(
            workflow_id=definition.id,
            execution_id=execution_id,
            status=status,
            output=context.data,
            error=error,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(context.started_at)),
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(context.completed_at)) if context.completed_at else None,
            node_executions=context.get_history(),
        )

    async def _execute_node(self, definition: WorkflowDefinition, context: WorkflowContext, node_id: str):
        """执行单个节点"""
        node = definition.get_node_by_id(node_id)
        if not node:
            raise ValueError(f"节点 {node_id} 不存在")

        logger.debug(f"执行节点: {node_id} ({node.name})")

        if isinstance(node, StartNode):
            await self._execute_start_node(node, context)
        elif isinstance(node, EndNode):
            await self._execute_end_node(node, context)
            return
        elif isinstance(node, TaskNode):
            await self._execute_task_node(node, context)
        elif isinstance(node, ConditionNode):
            await self._execute_condition_node(definition, node, context)
            return
        elif isinstance(node, ParallelNode):
            await self._execute_parallel_node(definition, node, context)
            return
        elif isinstance(node, LoopNode):
            await self._execute_loop_node(definition, node, context)
            return
        else:
            raise ValueError(f"未知节点类型: {node.type}")

        # 继续执行下一个节点
        for next_node_id in node.next_nodes:
            await self._execute_node(definition, context, next_node_id)

    async def _execute_start_node(self, node: StartNode, context: WorkflowContext):
        """执行开始节点"""
        context.record_execution(node.id, node.type, {"status": "started"})
        logger.debug(f"开始节点执行完成: {node.id}")

    async def _execute_end_node(self, node: EndNode, context: WorkflowContext):
        """执行结束节点"""
        context.record_execution(node.id, node.type, {"status": "completed"})
        logger.debug(f"结束节点执行完成: {node.id}")

    async def _execute_task_node(self, node: TaskNode, context: WorkflowContext):
        """执行任务节点"""
        try:
            result = await self._execute_task(node.task_type, node.task_config, context)
            context.record_execution(node.id, node.type, result)
            logger.debug(f"任务节点执行完成: {node.id}, 结果: {result}")
        except Exception as e:
            context.record_execution(node.id, node.type, None, str(e))
            raise

    async def _execute_condition_node(self, definition: WorkflowDefinition, node: ConditionNode, context: WorkflowContext):
        """执行条件节点"""
        try:
            condition_result = self._evaluate_condition(node.condition, context)
            context.record_execution(node.id, node.type, {"condition_result": condition_result})

            next_node_id = node.true_branch if condition_result else node.false_branch
            logger.debug(f"条件节点 {node.id} 计算结果: {condition_result}, 进入分支: {next_node_id}")

            await self._execute_node(definition, context, next_node_id)
        except Exception as e:
            context.record_execution(node.id, node.type, None, str(e))
            raise

    async def _execute_parallel_node(self, definition: WorkflowDefinition, node: ParallelNode, context: WorkflowContext):
        """执行并行节点"""
        try:
            tasks = []
            for branch in node.branches:
                tasks.append(self._execute_branch(definition, context, branch))

            results = await asyncio.gather(*tasks)
            context.record_execution(node.id, node.type, {"branch_results": results})

            logger.debug(f"并行节点 {node.id} 所有分支执行完成，进入汇合节点: {node.join_node}")
            await self._execute_node(definition, context, node.join_node)
        except Exception as e:
            context.record_execution(node.id, node.type, None, str(e))
            raise

    async def _execute_branch(self, definition: WorkflowDefinition, context: WorkflowContext, branch: List[str]):
        """执行并行分支"""
        for node_id in branch:
            await self._execute_node(definition, context, node_id)
        return {"branch_nodes": branch, "status": "completed"}

    async def _execute_loop_node(self, definition: WorkflowDefinition, node: LoopNode, context: WorkflowContext):
        """执行循环节点"""
        loop_count = 0
        max_iterations = context.get("max_iterations", 100)

        try:
            while self._evaluate_condition(node.loop_condition, context) and loop_count < max_iterations:
                loop_count += 1
                logger.debug(f"循环节点 {node.id} 第 {loop_count} 次迭代")

                for node_id in node.loop_body:
                    await self._execute_node(definition, context, node_id)

            context.record_execution(node.id, node.type, {"loop_count": loop_count, "max_iterations": max_iterations})
            logger.debug(f"循环节点 {node.id} 退出，共执行 {loop_count} 次")

            await self._execute_node(definition, context, node.exit_node)
        except Exception as e:
            context.record_execution(node.id, node.type, None, str(e))
            raise

    def _evaluate_condition(self, condition: str, context: WorkflowContext) -> bool:
        """评估条件表达式"""
        try:
            # 使用上下文数据作为局部变量来评估表达式
            local_vars = context.data.copy()
            result = eval(condition, {}, local_vars)
            return bool(result)
        except Exception as e:
            logger.error(f"条件表达式评估失败: {condition}, 错误: {str(e)}")
            raise ValueError(f"条件表达式评估失败: {condition}")

    async def _execute_task(self, task_type: str, task_config: Dict[str, Any], context: WorkflowContext) -> Any:
        """执行任务"""
        logger.debug(f"执行任务: {task_type}, 配置: {task_config}")

        # 模拟任务执行
        await asyncio.sleep(task_config.get("delay", 0))

        # 根据任务类型执行不同的逻辑
        if task_type == "log":
            message = task_config.get("message", "")
            logger.info(f"任务日志: {message}")
            return {"message": message, "logged": True}
        elif task_type == "set_variable":
            key = task_config.get("key")
            value = task_config.get("value")
            context.set(key, value)
            return {"key": key, "value": value, "action": "set"}
        elif task_type == "compute":
            expression = task_config.get("expression", "")
            result = eval(expression, {}, context.data)
            return {"expression": expression, "result": result}
        elif task_type == "delay":
            delay = task_config.get("seconds", 1)
            await asyncio.sleep(delay)
            return {"delay": delay, "status": "completed"}
        else:
            logger.warning(f"未知任务类型: {task_type}")
            return {"task_type": task_type, "status": "unknown"}

    def get_status(self, execution_id: str) -> Optional[ExecutionResult]:
        """获取执行状态"""
        context = self._executions.get(execution_id)
        if not context:
            return None

        status = WorkflowStatus.RUNNING if execution_id in self._running_workflows else WorkflowStatus.COMPLETED

        return ExecutionResult(
            workflow_id="",
            execution_id=execution_id,
            status=status,
            output=context.data,
            error=None,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(context.started_at)),
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(context.completed_at)) if context.completed_at else None,
            node_executions=context.get_history(),
        )

    def stop(self, execution_id: str) -> bool:
        """停止流程执行"""
        if execution_id in self._running_workflows:
            self._running_workflows.discard(execution_id)
            context = self._executions.get(execution_id)
            if context:
                context.mark_completed()
            logger.info(f"流程执行已停止: {execution_id}")
            return True
        return False

    def list_executions(self) -> List[str]:
        """获取所有执行中的流程ID"""
        return list(self._running_workflows)


# 全局引擎实例
_workflow_engine = WorkflowEngine()


def get_workflow_engine() -> WorkflowEngine:
    """获取全局流程引擎实例"""
    return _workflow_engine
