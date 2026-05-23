"""Workflow API 路由

提供流程定义、执行、状态查询和版本管理功能。
"""

import traceback
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.utils.logger import get_logger
from backend.workflow.definition import WorkflowParser, WorkflowValidator
from backend.workflow.engine import WorkflowStatus, get_workflow_engine
from backend.workflow.version_manager import VersionInfo, get_version_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class WorkflowDefineRequest(BaseModel):
    """定义流程请求模型"""

    workflow: Dict[str, Any] = Field(..., description="流程定义")
    version_description: Optional[str] = Field(default=None, description="版本描述")


class WorkflowExecuteRequest(BaseModel):
    """执行流程请求模型"""

    workflow_id: str = Field(..., description="流程ID")
    version: Optional[str] = Field(default=None, description="版本号，默认使用活跃版本")
    input_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="输入数据")


class WorkflowStatusRequest(BaseModel):
    """查询流程状态请求模型"""

    execution_id: str = Field(..., description="执行ID")


class WorkflowStopRequest(BaseModel):
    """停止流程请求模型"""

    execution_id: str = Field(..., description="执行ID")


class WorkflowRollbackRequest(BaseModel):
    """回滚版本请求模型"""

    workflow_id: str = Field(..., description="流程ID")
    target_version: str = Field(..., description="目标版本号")


class WorkflowVersionListRequest(BaseModel):
    """版本列表请求模型"""

    workflow_id: str = Field(..., description="流程ID")


class WorkflowCompareRequest(BaseModel):
    """版本对比请求模型"""

    workflow_id: str = Field(..., description="流程ID")
    from_version: str = Field(..., description="源版本号")
    to_version: str = Field(..., description="目标版本号")


class WorkflowDefineResponse(BaseModel):
    """定义流程响应模型"""

    success: bool = Field(..., description="是否成功")
    workflow_id: str = Field(..., description="流程ID")
    version: str = Field(..., description="版本号")
    message: str = Field(..., description="消息")


class WorkflowExecuteResponse(BaseModel):
    """执行流程响应模型"""

    success: bool = Field(..., description="是否成功")
    execution_id: str = Field(..., description="执行ID")
    status: WorkflowStatus = Field(..., description="执行状态")
    message: str = Field(..., description="消息")


class WorkflowStatusResponse(BaseModel):
    """流程状态响应模型"""

    execution_id: str = Field(..., description="执行ID")
    status: WorkflowStatus = Field(..., description="执行状态")
    output: Optional[Dict[str, Any]] = Field(default=None, description="输出数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    node_executions: Optional[List[Dict[str, Any]]] = Field(default=None, description="节点执行记录")


class WorkflowStopResponse(BaseModel):
    """停止流程响应模型"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")


class WorkflowRollbackResponse(BaseModel):
    """回滚版本响应模型"""

    success: bool = Field(..., description="是否成功")
    workflow_id: str = Field(..., description="流程ID")
    target_version: str = Field(..., description="目标版本号")
    message: str = Field(..., description="消息")


class WorkflowVersionListResponse(BaseModel):
    """版本列表响应模型"""

    workflow_id: str = Field(..., description="流程ID")
    versions: List[VersionInfo] = Field(default_factory=list, description="版本列表")


class WorkflowCompareResponse(BaseModel):
    """版本对比响应模型"""

    workflow_id: str = Field(..., description="流程ID")
    from_version: str = Field(..., description="源版本号")
    to_version: str = Field(..., description="目标版本号")
    added_nodes: List[str] = Field(default_factory=list, description="新增节点ID列表")
    removed_nodes: List[str] = Field(default_factory=list, description="删除节点ID列表")
    modified_nodes: List[str] = Field(default_factory=list, description="修改节点ID列表")
    changed_config: List[str] = Field(default_factory=list, description="变更的配置项")


@router.post("/define", response_model=WorkflowDefineResponse)
async def define_workflow(request: WorkflowDefineRequest):
    """定义流程

    创建或更新流程定义，并保存版本。
    """
    try:
        definition = WorkflowParser.from_dict(request.workflow)

        errors = WorkflowValidator.validate(definition)
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"success": False, "message": "流程定义验证失败", "errors": errors},
            )

        version_manager = get_version_manager()
        version_info = version_manager.save_version(definition, request.version_description)

        logger.info(f"流程定义成功: {definition.id} v{definition.version}")

        return WorkflowDefineResponse(
            success=True,
            workflow_id=definition.id,
            version=version_info.version,
            message="流程定义成功",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"流程定义失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "流程定义失败", "error": str(e)},
        )


@router.post("/execute", response_model=WorkflowExecuteResponse)
async def execute_workflow(request: WorkflowExecuteRequest):
    """执行流程

    根据流程ID执行流程实例。
    """
    try:
        version_manager = get_version_manager()

        if request.version:
            definition = version_manager.get_version(request.workflow_id, request.version)
        else:
            definition = version_manager.get_active_version(request.workflow_id)

        if not definition:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "流程定义不存在"},
            )

        engine = get_workflow_engine()
        result = await engine.execute(definition, request.input_data)

        return WorkflowExecuteResponse(
            success=True,
            execution_id=result.execution_id,
            status=result.status,
            message="流程执行成功" if result.status == WorkflowStatus.COMPLETED else "流程执行中",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"流程执行失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "流程执行失败", "error": str(e)},
        )


@router.get("/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(execution_id: str):
    """查询流程状态

    根据执行ID查询流程执行状态。
    """
    try:
        engine = get_workflow_engine()
        result = engine.get_status(execution_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail={"execution_id": execution_id, "status": "not_found", "message": "执行记录不存在"},
            )

        return WorkflowStatusResponse(
            execution_id=result.execution_id,
            status=result.status,
            output=result.output,
            error=result.error,
            node_executions=result.node_executions,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"查询流程状态失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"execution_id": execution_id, "message": "查询失败", "error": str(e)},
        )


@router.post("/stop", response_model=WorkflowStopResponse)
async def stop_workflow(request: WorkflowStopRequest):
    """停止流程

    停止正在执行的流程实例。
    """
    try:
        engine = get_workflow_engine()
        success = engine.stop(request.execution_id)

        if success:
            logger.info(f"流程已停止: {request.execution_id}")
            return WorkflowStopResponse(success=True, message="流程已停止")
        else:
            raise HTTPException(
                status_code=404,
                detail={"success": False, "message": "执行记录不存在或已停止"},
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"停止流程失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "停止流程失败", "error": str(e)},
        )


@router.get("/versions", response_model=WorkflowVersionListResponse)
async def get_workflow_versions(workflow_id: str):
    """获取版本列表

    获取指定流程的所有版本。
    """
    try:
        version_manager = get_version_manager()
        versions = version_manager.list_versions(workflow_id)

        return WorkflowVersionListResponse(
            workflow_id=workflow_id,
            versions=versions,
        )

    except Exception as e:
        logger.error(f"获取版本列表失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"workflow_id": workflow_id, "message": "获取版本列表失败", "error": str(e)},
        )


@router.post("/rollback", response_model=WorkflowRollbackResponse)
async def rollback_workflow(request: WorkflowRollbackRequest):
    """回滚版本

    将流程回滚到指定版本。
    """
    try:
        version_manager = get_version_manager()
        success = version_manager.rollback(request.workflow_id, request.target_version)

        if success:
            logger.info(f"流程 {request.workflow_id} 已回滚到版本 {request.target_version}")
            return WorkflowRollbackResponse(
                success=True,
                workflow_id=request.workflow_id,
                target_version=request.target_version,
                message=f"已成功回滚到版本 {request.target_version}",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "workflow_id": request.workflow_id,
                    "target_version": request.target_version,
                    "message": "回滚失败，流程或版本不存在",
                },
            )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"回滚版本失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "workflow_id": request.workflow_id,
                "message": "回滚失败",
                "error": str(e),
            },
        )


@router.post("/compare", response_model=WorkflowCompareResponse)
async def compare_workflow_versions(request: WorkflowCompareRequest):
    """对比版本差异

    对比两个版本之间的差异。
    """
    try:
        version_manager = get_version_manager()
        diff = version_manager.compare_versions(
            request.workflow_id,
            request.from_version,
            request.to_version,
        )

        if not diff:
            raise HTTPException(
                status_code=400,
                detail={
                    "workflow_id": request.workflow_id,
                    "message": "版本不存在",
                },
            )

        return WorkflowCompareResponse(
            workflow_id=diff.workflow_id,
            from_version=diff.from_version,
            to_version=diff.to_version,
            added_nodes=diff.added_nodes,
            removed_nodes=diff.removed_nodes,
            modified_nodes=diff.modified_nodes,
            changed_config=diff.changed_config,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"版本对比失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "workflow_id": request.workflow_id,
                "message": "版本对比失败",
                "error": str(e),
            },
        )


@router.get("/active-version")
async def get_active_workflow_version(workflow_id: str):
    """获取活跃版本

    获取指定流程的当前活跃版本。
    """
    try:
        version_manager = get_version_manager()
        definition = version_manager.get_active_version(workflow_id)

        if not definition:
            raise HTTPException(
                status_code=404,
                detail={"workflow_id": workflow_id, "message": "流程不存在"},
            )

        return {
            "workflow_id": definition.id,
            "version": definition.version,
            "name": definition.name,
            "description": definition.description,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"获取活跃版本失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"workflow_id": workflow_id, "message": "获取活跃版本失败", "error": str(e)},
        )


@router.get("/running")
async def get_running_workflows():
    """获取正在运行的流程列表"""
    try:
        engine = get_workflow_engine()
        execution_ids = engine.list_executions()

        return {"running_executions": execution_ids, "count": len(execution_ids)}

    except Exception as e:
        logger.error(f"获取运行中流程失败: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"message": "获取运行中流程失败", "error": str(e)},
        )
