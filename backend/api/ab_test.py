"""
A/B 测试 API 接口
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.core.ab_test import (
    ABTestManager,
    ExperimentType,
    ExperimentStatus,
    ExperimentResult,
    get_ab_test_manager
)


router = APIRouter(prefix="/api/ab-test", tags=["A/B 测试"])


class CreateExperimentRequest(BaseModel):
    """创建实验请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    experiment_type: str = Field(..., description="retrieval_strategy|prompt_template|model_params|reranking")
    target_metric: str = Field(default="user_satisfaction")
    minimum_sample_size: int = Field(default=100, ge=10, le=10000)
    variants: List[dict] = Field(..., min_length=2, max_length=5)


class RecordResultRequest(BaseModel):
    """记录结果请求"""
    experiment_id: str
    variant_id: str
    session_id: str
    user_id: Optional[str] = None
    query: str = ""
    input_config: dict = {}
    output_config: dict = {}
    metrics: dict = {}
    feedback: Optional[int] = Field(None, ge=1, le=5)


@router.post("/experiments")
async def create_experiment(request: CreateExperimentRequest):
    """创建 A/B 测试实验"""
    try:
        # 验证实验类型
        try:
            exp_type = ExperimentType(request.experiment_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的实验类型")
        
        # 验证变体配置
        for variant in request.variants:
            if "name" not in variant:
                raise HTTPException(status_code=400, detail="每个变体必须有名称")
            if "traffic_percentage" not in variant:
                raise HTTPException(status_code=400, detail="每个变体必须指定流量分配")
        
        manager = get_ab_test_manager()
        experiment = manager.create_experiment(
            name=request.name,
            description=request.description,
            experiment_type=exp_type,
            variants=request.variants,
            target_metric=request.target_metric,
            minimum_sample_size=request.minimum_sample_size
        )
        
        return {
            "success": True,
            "experiment_id": experiment.experiment_id,
            "message": "实验创建成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(experiment_id: str):
    """启动实验"""
    manager = get_ab_test_manager()
    success = manager.start_experiment(experiment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    return {"success": True, "message": "实验已启动"}


@router.post("/experiments/{experiment_id}/pause")
async def pause_experiment(experiment_id: str):
    """暂停实验"""
    manager = get_ab_test_manager()
    success = manager.pause_experiment(experiment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    return {"success": True, "message": "实验已暂停"}


@router.post("/experiments/{experiment_id}/complete")
async def complete_experiment(experiment_id: str):
    """完成实验"""
    manager = get_ab_test_manager()
    success = manager.complete_experiment(experiment_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="实验不存在")
    
    return {"success": True, "message": "实验已完成"}


@router.get("/experiments")
async def list_experiments():
    """获取所有实验列表"""
    manager = get_ab_test_manager()
    experiments = manager.get_all_experiments()
    return {"experiments": experiments}


@router.get("/experiments/{experiment_id}")
async def get_experiment(experiment_id: str):
    """获取实验详情"""
    manager = get_ab_test_manager()
    
    # 先检查实验是否存在
    experiments = manager.get_all_experiments()
    if not any(e["experiment_id"] == experiment_id for e in experiments):
        raise HTTPException(status_code=404, detail="实验不存在")
    
    results = manager.get_experiment_results(experiment_id)
    return results


@router.post("/assign")
async def assign_variant(
    experiment_id: str,
    x_session_id: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None)
):
    """为用户分配实验变体"""
    manager = get_ab_test_manager()
    variant = manager.assign_variant(
        experiment_id=experiment_id,
        user_id=x_user_id,
        session_id=x_session_id
    )
    
    if variant is None:
        raise HTTPException(status_code=404, detail="实验不存在或未运行")
    
    return {
        "variant_id": variant.variant_id,
        "variant_name": variant.name,
        "config": variant.config
    }


@router.post("/results")
async def record_result(request: RecordResultRequest):
    """记录实验结果"""
    manager = get_ab_test_manager()
    
    result = ExperimentResult(
        experiment_id=request.experiment_id,
        variant_id=request.variant_id,
        session_id=request.session_id,
        user_id=request.user_id,
        query=request.query,
        input_config=request.input_config,
        output_config=request.output_config,
        metrics=request.metrics
    )
    result.feedback = request.feedback
    
    success = manager.record_result(result)
    
    if not success:
        raise HTTPException(status_code=400, detail="记录失败")
    
    return {"success": True, "message": "结果已记录"}


@router.post("/feedback")
async def submit_feedback(
    experiment_id: str,
    variant_id: str,
    session_id: str,
    feedback: int = Field(..., ge=1, le=5),
    x_user_id: Optional[str] = Header(None)
):
    """提交用户反馈"""
    manager = get_ab_test_manager()
    
    result = ExperimentResult(
        experiment_id=experiment_id,
        variant_id=variant_id,
        session_id=session_id,
        user_id=x_user_id,
        feedback=feedback
    )
    
    success = manager.record_result(result)
    
    if not success:
        raise HTTPException(status_code=400, detail="提交失败")
    
    return {"success": True, "message": "反馈已提交"}


# 预设的 A/B 测试配置
PRESET_EXPERIMENTS = {
    "retrieval_comparison": {
        "name": "检索策略对比测试",
        "description": "对比 BM25、向量检索和混合检索的效果",
        "experiment_type": "retrieval_strategy",
        "variants": [
            {
                "name": "BM25 检索",
                "description": "仅使用 BM25 全文检索",
                "traffic_percentage": 33.33,
                "config": {"use_bm25": True, "use_vector": False, "use_rerank": False}
            },
            {
                "name": "向量检索",
                "description": "仅使用向量检索",
                "traffic_percentage": 33.33,
                "config": {"use_bm25": False, "use_vector": True, "use_rerank": False}
            },
            {
                "name": "混合检索 + 重排序",
                "description": "混合检索 + RRF 融合 + 重排序",
                "traffic_percentage": 33.34,
                "config": {"use_bm25": True, "use_vector": True, "use_rerank": True}
            }
        ]
    },
    "prompt_template": {
        "name": "提示词模板对比测试",
        "description": "对比不同提示词模板的效果",
        "experiment_type": "prompt_template",
        "variants": [
            {
                "name": "简洁模板",
                "description": "使用简洁的提示词",
                "traffic_percentage": 50,
                "config": {"template_type": "concise"}
            },
            {
                "name": "详细模板",
                "description": "使用详细的提示词",
                "traffic_percentage": 50,
                "config": {"template_type": "detailed"}
            }
        ]
    },
    "temperature_test": {
        "name": "温度参数对比测试",
        "description": "对比不同温度参数对回答质量的影响",
        "experiment_type": "model_params",
        "variants": [
            {
                "name": "低温度 (0.3)",
                "description": "更确定性、保守的回答",
                "traffic_percentage": 33.33,
                "config": {"temperature": 0.3}
            },
            {
                "name": "中等温度 (0.7)",
                "description": "平衡创造性和准确性",
                "traffic_percentage": 33.33,
                "config": {"temperature": 0.7}
            },
            {
                "name": "高温度 (1.0)",
                "description": "更有创意、多样的回答",
                "traffic_percentage": 33.34,
                "config": {"temperature": 1.0}
            }
        ]
    }
}


@router.get("/presets")
async def list_preset_experiments():
    """获取预设实验配置"""
    return {"presets": list(PRESET_EXPERIMENTS.keys())}


@router.post("/presets/{preset_name}")
async def create_preset_experiment(preset_name: str):
    """创建预设实验"""
    if preset_name not in PRESET_EXPERIMENTS:
        raise HTTPException(status_code=404, detail="预设实验不存在")
    
    preset = PRESET_EXPERIMENTS[preset_name]
    manager = get_ab_test_manager()
    
    try:
        exp_type = ExperimentType(preset["experiment_type"])
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的实验类型")
    
    experiment = manager.create_experiment(
        name=preset["name"],
        description=preset["description"],
        experiment_type=exp_type,
        variants=preset["variants"]
    )
    
    return {
        "success": True,
        "experiment_id": experiment.experiment_id,
        "message": f"预设实验 '{preset_name}' 创建成功"
    }
