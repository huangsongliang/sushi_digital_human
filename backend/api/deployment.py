"""部署管理 API 端点 - 支持版本管理、灰度发布和 A/B 测试"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.deployment import (
    ExperimentResult,
    ExperimentStatus,
    TrafficStrategy,
    VersionStatus,
    VersionType,
    get_deployment_ab_test_manager,
    get_traffic_controller,
    get_version_manager,
)

router = APIRouter(prefix="/api/deployment", tags=["部署管理"])


class RegisterVersionRequest(BaseModel):
    """注册版本请求"""

    version_name: str = Field(..., min_length=1, max_length=100)
    version_code: str = Field(..., min_length=1, max_length=50)
    version_type: str = Field(..., description="major|minor|patch|hotfix")
    config: Optional[Dict[str, Any]] = Field(default=None)
    changelog: Optional[str] = Field(default="", max_length=1000)
    tags: Optional[List[str]] = Field(default=None)
    dependencies: Optional[Dict[str, str]] = Field(default=None)


class UpdateVersionStatusRequest(BaseModel):
    """更新版本状态请求"""

    status: str = Field(..., description="draft|staging|canary|production|rollback|deprecated")


class UpdateRolloutRequest(BaseModel):
    """更新灰度发布请求"""

    percentage: float = Field(..., ge=0, le=100)


class CanaryConfigRequest(BaseModel):
    """灰度配置请求"""

    primary_version_id: str = Field(..., description="主版本ID")
    canary_version_id: str = Field(..., description="灰度版本ID")
    strategy: str = Field(default="percentage", description="percentage|user_hash|region|weighted")
    weights: Optional[List[Dict[str, Any]]] = Field(default=None)
    user_ids: Optional[List[str]] = Field(default=None)
    ip_ranges: Optional[List[str]] = Field(default=None)
    regions: Optional[List[str]] = Field(default=None)


class CreateExperimentRequest(BaseModel):
    """创建实验请求"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    groups: List[Dict[str, Any]] = Field(..., min_length=2, max_length=5)
    config: Optional[Dict[str, Any]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


class RecordExperimentResultRequest(BaseModel):
    """记录实验结果请求"""

    group_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    impressions: int = Field(default=1, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: float = Field(default=0.0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0)
    custom_metrics: Optional[Dict[str, Any]] = Field(default=None)


@router.get("/versions")
async def list_versions(
    status: Optional[str] = Query(None, description="按状态筛选"),
    tags: Optional[str] = Query(None, description="按标签筛选，逗号分隔"),
):
    """获取版本列表"""
    try:
        version_manager = get_version_manager()

        filter_status = None
        if status:
            try:
                filter_status = VersionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的版本状态")

        filter_tags = None
        if tags:
            filter_tags = [t.strip() for t in tags.split(",")]

        versions = version_manager.list_versions(status=filter_status, tags=filter_tags)

        return {
            "success": True,
            "count": len(versions),
            "versions": [v.to_dict() for v in versions],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions")
async def register_version(request: RegisterVersionRequest):
    """注册新版本"""
    try:
        version_manager = get_version_manager()

        try:
            version_type = VersionType(request.version_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的版本类型")

        version = version_manager.register_version(
            version_name=request.version_name,
            version_code=request.version_code,
            version_type=version_type,
            created_by="system",
            config=request.config,
            changelog=request.changelog or "",
            tags=request.tags,
            dependencies=request.dependencies,
        )

        return {
            "success": True,
            "version_id": version.version_id,
            "message": f"版本 {request.version_code} 注册成功",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}")
async def get_version(version_id: str):
    """获取版本详情"""
    version_manager = get_version_manager()
    version = version_manager.get_version(version_id)

    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"success": True, "version": version.to_dict()}


@router.post("/versions/{version_id}/status")
async def update_version_status(version_id: str, request: UpdateVersionStatusRequest):
    """更新版本状态"""
    try:
        version_manager = get_version_manager()

        try:
            new_status = VersionStatus(request.status)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的版本状态")

        success = version_manager.update_version_status(version_id, new_status)

        if not success:
            raise HTTPException(status_code=404, detail="版本不存在")

        return {"success": True, "message": f"版本状态已更新为 {request.status}"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/versions/{version_id}/rollout")
async def update_rollout_percentage(version_id: str, request: UpdateRolloutRequest):
    """更新灰度发布百分比"""
    try:
        version_manager = get_version_manager()
        success = version_manager.update_rollout_percentage(version_id, request.percentage)

        if not success:
            raise HTTPException(status_code=404, detail="版本不存在")

        return {"success": True, "message": f"灰度发布百分比已更新为 {request.percentage}%"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions/{version_id}/compare")
async def compare_versions(version_id: str):
    """对比版本与前一个版本"""
    version_manager = get_version_manager()
    comparison = version_manager.compare_with_previous(version_id)

    if not comparison:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {"success": True, "comparison": comparison}


@router.post("/canary")
async def create_canary_config(request: CanaryConfigRequest):
    """创建灰度配置"""
    try:
        traffic_controller = get_traffic_controller()

        try:
            strategy = TrafficStrategy(request.strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的分流策略")

        config = traffic_controller.create_canary_config(
            primary_version_id=request.primary_version_id,
            canary_version_id=request.canary_version_id,
            strategy=strategy,
            weights=request.weights,
            user_ids=request.user_ids,
            ip_ranges=request.ip_ranges,
            regions=request.regions,
        )

        return {
            "success": True,
            "canary_id": config.canary_id,
            "message": "灰度配置创建成功",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/canary")
async def list_canary_configs():
    """获取灰度配置列表"""
    try:
        traffic_controller = get_traffic_controller()
        configs = traffic_controller.list_canary_configs()

        return {
            "success": True,
            "count": len(configs),
            "configs": [c.to_dict() for c in configs],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/canary/{canary_id}")
async def get_canary_config(canary_id: str):
    """获取灰度配置详情"""
    traffic_controller = get_traffic_controller()
    config = traffic_controller.get_canary_config(canary_id)

    if not config:
        raise HTTPException(status_code=404, detail="灰度配置不存在")

    return {"success": True, "config": config.to_dict()}


@router.post("/canary/{canary_id}")
async def update_canary_config(
    canary_id: str,
    request: CanaryConfigRequest,
):
    """更新灰度配置"""
    try:
        traffic_controller = get_traffic_controller()

        try:
            strategy = TrafficStrategy(request.strategy)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的分流策略")

        success = traffic_controller.update_canary_config(
            canary_id=canary_id,
            strategy=strategy,
            weights=request.weights,
            user_ids=request.user_ids,
            ip_ranges=request.ip_ranges,
            regions=request.regions,
        )

        if not success:
            raise HTTPException(status_code=404, detail="灰度配置不存在")

        return {"success": True, "message": "灰度配置已更新"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/canary/{canary_id}")
async def delete_canary_config(canary_id: str):
    """删除灰度配置"""
    traffic_controller = get_traffic_controller()
    success = traffic_controller.delete_canary_config(canary_id)

    if not success:
        raise HTTPException(status_code=404, detail="灰度配置不存在")

    return {"success": True, "message": "灰度配置已删除"}


@router.post("/canary/{canary_id}/route")
async def route_request(
    canary_id: str,
    x_user_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
):
    """路由请求到指定版本"""
    try:
        traffic_controller = get_traffic_controller()

        ip_address = None
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()

        version_id = traffic_controller.route_request(
            canary_id=canary_id,
            user_id=x_user_id,
            session_id=x_session_id,
            ip_address=ip_address,
        )

        return {
            "success": True,
            "version_id": version_id,
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/canary/{canary_id}/stats")
async def get_canary_stats(canary_id: str):
    """获取灰度流量统计"""
    traffic_controller = get_traffic_controller()
    stats = traffic_controller.get_traffic_stats(canary_id)

    if not stats:
        raise HTTPException(status_code=404, detail="灰度配置不存在")

    return {"success": True, "stats": stats}


@router.post("/canary/{canary_id}/weights")
async def adjust_canary_weights(
    canary_id: str,
    canary_weight: float = Query(..., ge=0, le=100),
):
    """调整灰度权重"""
    try:
        traffic_controller = get_traffic_controller()
        success = traffic_controller.adjust_weights(canary_id, canary_weight)

        if not success:
            raise HTTPException(status_code=404, detail="灰度配置不存在")

        return {
            "success": True,
            "message": f"权重已调整: canary={canary_weight}%, primary={100 - canary_weight}%",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments")
async def list_experiments(
    status: Optional[str] = Query(None, description="按状态筛选"),
):
    """获取实验列表"""
    try:
        ab_test_manager = get_deployment_ab_test_manager()

        filter_status = None
        if status:
            try:
                filter_status = ExperimentStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的实验状态")

        experiments = ab_test_manager.list_experiments(status=filter_status)

        return {
            "success": True,
            "count": len(experiments),
            "experiments": experiments,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments")
async def create_experiment(request: CreateExperimentRequest):
    """创建实验"""
    try:
        ab_test_manager = get_deployment_ab_test_manager()

        for group in request.groups:
            if "version_id" not in group:
                raise HTTPException(status_code=400, detail="每个分组必须指定 version_id")
            if "name" not in group:
                raise HTTPException(status_code=400, detail="每个分组必须指定 name")
            if "traffic_percentage" not in group:
                raise HTTPException(status_code=400, detail="每个分组必须指定 traffic_percentage")

        experiment = ab_test_manager.create_experiment(
            name=request.name,
            description=request.description,
            groups=request.groups,
            config=request.config,
            tags=request.tags,
        )

        return {
            "success": True,
            "experiment_id": experiment.experiment_id,
            "message": f"实验 '{request.name}' 创建成功",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """获取实验详情"""
    ab_test_manager = get_deployment_ab_test_manager()
    experiment = ab_test_manager.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "experiment": experiment.to_dict()}


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """启动实验"""
    ab_test_manager = get_deployment_ab_test_manager()
    success = ab_test_manager.start_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "message": "实验已启动"}


@router.post("/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str):
    """暂停实验"""
    ab_test_manager = get_deployment_ab_test_manager()
    success = ab_test_manager.pause_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "message": "实验已暂停"}


@router.post("/experiments/{experiment_id}/complete")
async def complete_experiment(experiment_id: str):
    """完成实验"""
    ab_test_manager = get_deployment_ab_test_manager()
    success = ab_test_manager.complete_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "message": "实验已完成"}


@router.post("/experiments/{experiment_id}/archive")
async def archive_experiment(experiment_id: str):
    """归档实验"""
    ab_test_manager = get_deployment_ab_test_manager()
    success = ab_test_manager.archive_experiment(experiment_id)

    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "message": "实验已归档"}


@router.get("/experiments/{experiment_id}/results")
async def get_experiment_results(experiment_id: str):
    """获取实验结果分析"""
    ab_test_manager = get_deployment_ab_test_manager()
    results = ab_test_manager.get_experiment_results(experiment_id)

    if not results:
        raise HTTPException(status_code=404, detail="实验不存在")

    return {"success": True, "results": results}


@router.post("/experiments/{experiment_id}/assign")
async def assign_experiment_group(
    experiment_id: str,
    x_user_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    """为用户分配实验分组"""
    ab_test_manager = get_deployment_ab_test_manager()
    group = ab_test_manager.assign_group(
        experiment_id=experiment_id,
        user_id=x_user_id,
        session_id=x_session_id,
    )

    if not group:
        raise HTTPException(status_code=404, detail="实验不存在或未运行")

    return {
        "success": True,
        "group_id": group.group_id,
        "group_name": group.name,
        "version_id": group.version_id,
        "config": group.config,
    }


@router.post("/experiments/{experiment_id}/results")
async def record_experiment_result(
    experiment_id: str,
    request: RecordExperimentResultRequest,
):
    """记录实验结果"""
    try:
        ab_test_manager = get_deployment_ab_test_manager()
        experiment = ab_test_manager.get_experiment(experiment_id)

        if not experiment:
            raise HTTPException(status_code=404, detail="实验不存在")

        result = ExperimentResult(
            experiment_id=experiment_id,
            group_id=request.group_id,
            timestamp=datetime.now(),
            user_id=request.user_id,
            session_id=request.session_id,
            impressions=request.impressions,
            clicks=request.clicks,
            conversions=request.conversions,
            revenue=request.revenue,
            latency_ms=request.latency_ms,
            custom_metrics=request.custom_metrics or {},
        )

        success = ab_test_manager.record_result(result)

        if not success:
            raise HTTPException(status_code=400, detail="记录失败")

        return {"success": True, "message": "结果已记录"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
