"""多Agent协作框架 API 端点"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.messaging import AgentMessage, MessageType, message_queue
from backend.agents.parallel_engine import parallel_engine
from backend.agents.role_manager import AgentCapability, role_manager
from backend.agents.task_splitter import Task, TaskPriority, task_splitter
from backend.database.session import get_db
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


class CreateRoleRequest(BaseModel):
    """创建角色请求模型"""

    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    capabilities: List[str] = Field(default_factory=list, description="角色能力列表")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "文档检索专家",
                "description": "负责文档检索和信息提取",
                "capabilities": ["document_retrieval", "knowledge_graph_query"],
            }
        }
    }


class CreateRoleResponse(BaseModel):
    """创建角色响应模型"""

    id: Optional[int] = Field(default=None, description="角色ID")
    name: str = Field(..., description="角色名称")
    description: Optional[str] = Field(default=None, description="角色描述")
    capabilities: List[str] = Field(default_factory=list, description="角色能力列表")
    is_active: bool = Field(default=True, description="是否启用")


class SplitTaskRequest(BaseModel):
    """任务拆分请求模型"""

    query: str = Field(..., description="用户查询")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "请分析2024年的销售数据，并生成一份详细的报告",
                "context": {"user_id": "123", "time_range": "2024-01-01至2024-12-31"},
            }
        }
    }


class SplitTaskResponse(BaseModel):
    """任务拆分响应模型"""

    tasks: List[Dict[str, Any]] = Field(default_factory=list, description="拆分后的任务列表")
    task_count: int = Field(..., description="任务数量")


class ExecuteTaskRequest(BaseModel):
    """执行任务请求模型"""

    tasks: List[Dict[str, Any]] = Field(..., description="任务列表")
    sequential: bool = Field(default=False, description="是否串行执行")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tasks": [
                    {
                        "id": "task-abc123",
                        "name": "数据查询",
                        "description": "查询销售数据",
                        "capability_requirements": ["data_analysis"],
                        "priority": "high",
                    }
                ],
                "sequential": False,
            }
        }
    }


class ExecuteTaskResponse(BaseModel):
    """执行任务响应模型"""

    results: List[Dict[str, Any]] = Field(default_factory=list, description="执行结果列表")
    summary: Dict[str, Any] = Field(default_factory=dict, description="执行摘要")


class GetMessagesRequest(BaseModel):
    """获取消息请求模型"""

    agent_id: Optional[str] = Field(default=None, description="Agent ID")
    limit: int = Field(default=100, description="返回数量限制")


class SendMessageRequest(BaseModel):
    """发送消息请求模型"""

    sender_id: str = Field(..., description="发送者ID")
    receiver_id: str = Field(..., description="接收者ID")
    message_type: str = Field(..., description="消息类型")
    content: Dict[str, Any] = Field(default_factory=dict, description="消息内容")
    priority: int = Field(default=0, description="消息优先级")

    model_config = {
        "json_schema_extra": {
            "example": {
                "sender_id": "agent-coordinator",
                "receiver_id": "agent-doc-retrieval",
                "message_type": "data_request",
                "content": {"query": "查找相关文档"},
                "priority": 5,
            }
        }
    }


@router.post("/roles", response_model=CreateRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    request: CreateRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建Agent角色"""
    try:
        capabilities = []
        for cap_str in request.capabilities:
            try:
                capabilities.append(AgentCapability(cap_str))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的能力值: {cap_str}",
                )

        role = await role_manager.create_role(
            name=request.name,
            description=request.description,
            capabilities=capabilities,
            db=db,
        )

        return CreateRoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            capabilities=[c.value for c in role.capabilities],
            is_active=role.is_active,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"创建角色失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建角色失败",
        )


@router.get("/roles", response_model=List[CreateRoleResponse])
async def get_roles(
    db: AsyncSession = Depends(get_db),
):
    """获取角色列表"""
    try:
        roles = await role_manager.list_roles(db)

        return [
            CreateRoleResponse(
                id=role.id,
                name=role.name,
                description=role.description,
                capabilities=[c.value for c in role.capabilities],
                is_active=role.is_active,
            )
            for role in roles
        ]

    except Exception as e:
        logger.error(f"获取角色列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取角色列表失败",
        )


@router.post("/task", response_model=SplitTaskResponse)
async def split_task(request: SplitTaskRequest):
    """任务拆分接口"""
    try:
        tasks = await task_splitter.split_task(
            user_query=request.query,
            context=request.context,
        )

        task_dicts = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "capability_requirements": [c.value for c in task.capability_requirements],
                "priority": task.priority.value,
                "status": task.status.value,
                "dependencies": [d.task_id for d in task.dependencies],
                "assigned_role": task.assigned_role.name if task.assigned_role else None,
            }
            task_dicts.append(task_dict)

        return SplitTaskResponse(
            tasks=task_dicts,
            task_count=len(tasks),
        )

    except Exception as e:
        logger.error(f"任务拆分失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务拆分失败",
        )


@router.post("/execute", response_model=ExecuteTaskResponse)
async def execute_tasks(request: ExecuteTaskRequest):
    """执行任务接口"""
    try:
        tasks = []
        for task_data in request.tasks:
            capabilities = set()
            for cap_str in task_data.get("capability_requirements", []):
                try:
                    capabilities.add(AgentCapability(cap_str))
                except ValueError:
                    logger.warning(f"忽略无效能力: {cap_str}")

            task = Task(
                id=task_data.get("id", ""),
                name=task_data.get("name", "未命名任务"),
                description=task_data.get("description", ""),
                capability_requirements=capabilities,
                priority=TaskPriority(task_data.get("priority", "medium")),
            )
            tasks.append(task)

        async def dummy_executor(task: Task) -> Dict[str, Any]:
            """模拟任务执行器"""
            await asyncio.sleep(0.5)
            return {
                "task_id": task.id,
                "task_name": task.name,
                "result": f"任务 '{task.name}' 执行成功",
                "capabilities": [c.value for c in task.capability_requirements],
            }

        results = await parallel_engine.execute_tasks(
            tasks=tasks,
            executor=dummy_executor,
            sequential=request.sequential,
        )

        result_dicts = []
        for result in results:
            result_dict = {
                "task_id": result.task_id,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time_ms": result.execution_time_ms,
            }
            result_dicts.append(result_dict)

        summary = parallel_engine.aggregate_results(results)

        return ExecuteTaskResponse(
            results=result_dicts,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"执行任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="执行任务失败",
        )


@router.post("/messages")
async def send_message(request: SendMessageRequest):
    """发送消息"""
    try:
        try:
            message_type = MessageType(request.message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的消息类型: {request.message_type}",
            )

        message = AgentMessage(
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            message_type=message_type,
            content=request.content,
            priority=request.priority,
        )

        await message_queue.send_message(message)

        return {
            "code": 200,
            "message": "消息发送成功",
            "data": {"message_id": message.id},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送消息失败",
        )


@router.get("/messages")
async def get_messages(
    agent_id: Optional[str] = None,
    limit: int = 100,
):
    """获取消息列表"""
    try:
        if agent_id:
            queue_size = message_queue.get_queue_size(agent_id)
            return {
                "code": 200,
                "message": "success",
                "data": {
                    "agent_id": agent_id,
                    "queue_size": queue_size,
                    "messages": [],
                },
            }

        return {
            "code": 200,
            "message": "success",
            "data": {
                "queues": list(message_queue._queues.keys()),
            },
        }

    except Exception as e:
        logger.error(f"获取消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息失败",
        )


@router.get("/health")
async def agents_health():
    """多Agent框架健康检查"""
    try:
        summary = parallel_engine.get_task_summary()
        return {
            "status": "healthy",
            "components": {
                "role_manager": "active",
                "task_splitter": "active",
                "parallel_engine": "active",
                "message_queue": "active",
            },
            "task_summary": summary,
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="多Agent框架服务异常",
        )


@router.post("/broadcast")
async def broadcast_message(request: SendMessageRequest):
    """广播消息到所有Agent"""
    try:
        try:
            message_type = MessageType(request.message_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的消息类型: {request.message_type}",
            )

        message = AgentMessage(
            sender_id=request.sender_id,
            receiver_id="broadcast",
            message_type=message_type,
            content=request.content,
            priority=request.priority,
        )

        await message_queue.broadcast_message(message)

        return {
            "code": 200,
            "message": "消息广播成功",
            "data": {"message_id": message.id},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"广播消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="广播消息失败",
        )
