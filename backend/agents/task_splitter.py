"""任务拆分模块

负责基于LLM的任务拆分、优先级排序和Agent能力匹配。
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.generator.llm import get_llm
from backend.utils.logger import get_logger

from .role_manager import AgentCapability, AgentRole, RoleManager

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """任务优先级枚举"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskDependency(BaseModel):
    """任务依赖关系"""

    task_id: str = Field(..., description="依赖的任务ID")
    required_status: TaskStatus = Field(TaskStatus.COMPLETED, description="依赖任务需要达到的状态")


class Task(BaseModel):
    """任务数据模型"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="任务唯一标识")
    name: str = Field(..., description="任务名称")
    description: str = Field(..., description="任务描述")
    capability_requirements: Set[AgentCapability] = Field(default_factory=set, description="所需能力")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="任务优先级")
    status: TaskStatus = Field(TaskStatus.PENDING, description="任务状态")
    dependencies: List[TaskDependency] = Field(default_factory=list, description="依赖的任务列表")
    assigned_role: Optional[AgentRole] = Field(default=None, description="分配的角色")
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")
    progress: float = Field(default=0.0, description="任务进度(0-1)")
    created_at: float = Field(default_factory=lambda: ..., description="创建时间戳")
    started_at: Optional[float] = Field(default=None, description="开始执行时间")
    completed_at: Optional[float] = Field(default=None, description="完成时间")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "task-abc123",
                "name": "文档检索",
                "description": "检索与用户问题相关的文档",
                "capability_requirements": ["document_retrieval"],
                "priority": "high",
                "status": "pending",
                "dependencies": [],
                "assigned_role": None,
                "result": None,
                "error": None,
                "progress": 0.0,
            }
        }
    }


class TaskSplitter:
    """任务拆分器"""

    def __init__(self, role_manager: Optional[RoleManager] = None):
        self._role_manager = role_manager

    async def split_task(
        self,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Task]:
        """基于LLM拆分复杂任务为子任务列表

        Args:
            user_query: 用户查询
            context: 上下文信息

        Returns:
            拆分后的子任务列表
        """
        logger.info(f"开始任务拆分: {user_query}")

        llm = get_llm()

        prompt = self._build_task_split_prompt(user_query, context)

        try:
            response = await llm.acall(prompt)
            tasks = self._parse_llm_response(response)

            tasks = self._sort_by_priority(tasks)
            tasks = self._assign_roles(tasks)

            logger.info(f"任务拆分完成，共生成 {len(tasks)} 个子任务")
            return tasks

        except Exception as e:
            logger.error(f"任务拆分失败: {str(e)}")
            return [self._create_fallback_task(user_query)]

    def _build_task_split_prompt(self, user_query: str, context: Optional[Dict]) -> str:
        """构建任务拆分提示词"""
        capabilities = [cap.value for cap in AgentCapability]

        prompt = f"""
你是一个任务规划专家，需要将用户的复杂查询拆分成多个可执行的子任务。

用户查询: {user_query}

可用的Agent能力:
{', '.join(capabilities)}

请按照以下规则拆分任务:
1. 将复杂任务分解为2-5个独立的子任务
2. 每个子任务应该明确需要哪些能力
3. 考虑任务之间的依赖关系
4. 为每个任务分配合理的优先级(high/medium/low)

请返回JSON格式的任务列表，格式如下:
[
  {{
    "name": "任务名称",
    "description": "任务描述",
    "capability_requirements": ["需要的能力1", "需要的能力2"],
    "priority": "high|medium|low",
    "dependencies": ["依赖的任务ID"]
  }}
]
"""
        return prompt

    def _parse_llm_response(self, response: str) -> List[Task]:
        """解析LLM响应"""
        import json

        try:
            data = json.loads(response)
            tasks = []

            for idx, task_data in enumerate(data):
                capabilities = set()
                for cap_str in task_data.get("capability_requirements", []):
                    try:
                        capabilities.add(AgentCapability(cap_str))
                    except ValueError:
                        logger.warning(f"未知能力: {cap_str}")

                task = Task(
                    name=task_data.get("name", f"子任务 {idx + 1}"),
                    description=task_data.get("description", ""),
                    capability_requirements=capabilities,
                    priority=TaskPriority(task_data.get("priority", "medium")),
                    dependencies=[TaskDependency(task_id=d) for d in task_data.get("dependencies", [])],
                )
                tasks.append(task)

            return tasks

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return []

    def _sort_by_priority(self, tasks: List[Task]) -> List[Task]:
        """按优先级排序任务"""
        priority_order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}

        return sorted(
            tasks,
            key=lambda t: (priority_order[t.priority], len(t.dependencies)),
        )

    def _assign_roles(self, tasks: List[Task]) -> List[Task]:
        """为任务分配合适的角色"""
        if not self._role_manager:
            return tasks

        for task in tasks:
            if task.capability_requirements:
                matched_roles = self._role_manager.match_roles_by_capabilities(task.capability_requirements)
                if matched_roles:
                    task.assigned_role = matched_roles[0]
                    logger.debug(f"任务 '{task.name}' 分配角色: {matched_roles[0].name}")

        return tasks

    def _create_fallback_task(self, user_query: str) -> Task:
        """创建回退任务"""
        return Task(
            name="直接回答",
            description=f"直接处理用户查询: {user_query}",
            capability_requirements={AgentCapability.LLM_CHAT},
            priority=TaskPriority.HIGH,
        )

    def calculate_task_order(self, tasks: List[Task]) -> List[str]:
        """计算任务执行顺序（考虑依赖关系）

        Args:
            tasks: 任务列表

        Returns:
            任务ID的执行顺序列表
        """
        task_map = {task.id: task for task in tasks}
        completed = set()
        order = []
        remaining = set(tasks)

        while remaining:
            executable = [
                task
                for task in remaining
                if all(dep.task_id in completed or dep.task_id not in task_map for dep in task.dependencies)
            ]

            if not executable:
                logger.warning("检测到任务依赖循环")
                break

            executable.sort(key=lambda t: self._priority_to_number(t.priority), reverse=True)

            task = executable[0]
            order.append(task.id)
            completed.add(task.id)
            remaining.remove(task)

        return order

    def _priority_to_number(self, priority: TaskPriority) -> int:
        """将优先级转换为数值（用于排序）"""
        return {"high": 3, "medium": 2, "low": 1}[priority.value]

    def estimate_task_complexity(self, task: Task) -> float:
        """估算任务复杂度

        Args:
            task: 任务对象

        Returns:
            复杂度评分(0-1)
        """
        score = 0.0

        capability_count = len(task.capability_requirements)
        score += min(capability_count * 0.2, 0.4)

        dependency_count = len(task.dependencies)
        score += min(dependency_count * 0.15, 0.3)

        priority_score = {"high": 0.3, "medium": 0.2, "low": 0.1}[task.priority.value]
        score += priority_score

        return min(score, 1.0)


# 全局任务拆分器实例
task_splitter = TaskSplitter()
