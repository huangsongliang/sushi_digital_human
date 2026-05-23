"""调试工具链API路由"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.debug.breakpoints import breakpoint_manager
from backend.debug.debugger import debugger, StepMode
from backend.debug.prompt_debugger import prompt_debugger
from backend.debug.state_visualizer import state_visualizer

router = APIRouter(prefix="/api/debug", tags=["debug"])


class StepRequest(BaseModel):
    """单步执行请求"""
    execution_id: str = Field(..., description="执行ID")
    mode: str = Field(default="step_over", description="单步模式：step_into/step_over/step_out")


class ContinueRequest(BaseModel):
    """继续执行请求"""
    execution_id: str = Field(..., description="执行ID")


class PauseRequest(BaseModel):
    """暂停执行请求"""
    execution_id: str = Field(..., description="执行ID")


class BreakpointRequest(BaseModel):
    """断点设置请求"""
    location: str = Field(..., description="断点位置")
    condition: Optional[str] = Field(default=None, description="条件表达式")
    enabled: bool = Field(default=True, description="是否启用")


class PromptAnalysisRequest(BaseModel):
    """Prompt分析请求"""
    prompt: str = Field(..., description="要分析的Prompt内容")
    template_variables: Optional[Dict[str, Any]] = Field(default=None, description="模板变量")


@router.post("/step")
async def step_execution(req: StepRequest):
    """单步执行"""
    mode_map = {
        "step_into": StepMode.STEP_INTO,
        "step_over": StepMode.STEP_OVER,
        "step_out": StepMode.STEP_OUT,
    }

    mode = mode_map.get(req.mode)
    if not mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的单步模式: {req.mode}"
        )

    success = await debugger.step_execution(req.execution_id, mode)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行 {req.execution_id} 未找到或无法单步执行"
        )

    return {"code": 200, "message": "success", "data": {"execution_id": req.execution_id, "mode": req.mode}}


@router.post("/continue")
async def continue_execution(req: ContinueRequest):
    """继续执行"""
    success = await debugger.resume_execution(req.execution_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行 {req.execution_id} 未找到或无法继续"
        )

    return {"code": 200, "message": "success", "data": {"execution_id": req.execution_id}}


@router.post("/pause")
async def pause_execution(req: PauseRequest):
    """暂停执行"""
    success = await debugger.pause_execution(req.execution_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行 {req.execution_id} 未找到或无法暂停"
        )

    return {"code": 200, "message": "success", "data": {"execution_id": req.execution_id}}


@router.post("/breakpoints")
async def set_breakpoint(req: BreakpointRequest):
    """设置断点"""
    bp = breakpoint_manager.add_breakpoint(
        location=req.location,
        condition=req.condition,
        enabled=req.enabled,
    )

    return {"code": 200, "message": "success", "data": bp.to_dict()}


@router.get("/breakpoints")
async def get_breakpoints():
    """获取断点列表"""
    bps = breakpoint_manager.get_all_breakpoints()
    return {"code": 200, "message": "success", "data": [bp.to_dict() for bp in bps]}


@router.delete("/breakpoints/{breakpoint_id}")
async def delete_breakpoint(breakpoint_id: str):
    """删除断点"""
    success = breakpoint_manager.remove_breakpoint(breakpoint_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"断点 {breakpoint_id} 未找到"
        )

    return {"code": 200, "message": "success", "data": {"breakpoint_id": breakpoint_id}}


@router.get("/state/{execution_id}")
async def get_execution_state(execution_id: str):
    """获取执行状态"""
    state = await debugger.get_execution_state(execution_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行 {execution_id} 未找到"
        )

    summary = state_visualizer.get_state_summary(execution_id)
    if "error" in summary:
        summary["state"] = state.value
    else:
        summary["state"] = state.value

    return {"code": 200, "message": "success", "data": summary}


@router.get("/trace/{execution_id}")
async def get_execution_trace(execution_id: str):
    """获取执行轨迹"""
    trace = state_visualizer.get_trace(execution_id)
    if not trace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"执行轨迹 {execution_id} 未找到"
        )

    return {"code": 200, "message": "success", "data": trace.serialize()}


@router.post("/prompt/analyze")
async def analyze_prompt(req: PromptAnalysisRequest):
    """分析Prompt"""
    analysis = prompt_debugger.analyze_prompt(req.prompt, req.template_variables)

    result = {
        "injection_detected": analysis.injection_detected,
        "injection_patterns": analysis.injection_patterns,
        "token_count": analysis.token_count,
        "template_variables": analysis.template_variables,
        "template_errors": analysis.template_errors,
        "warnings": analysis.warnings,
        "suggestions": analysis.suggestions,
    }

    return {"code": 200, "message": "success", "data": result}


@router.get("/breakpoints/{breakpoint_id}")
async def get_breakpoint(breakpoint_id: str):
    """获取单个断点详情"""
    bp = breakpoint_manager.get_breakpoint(breakpoint_id)
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"断点 {breakpoint_id} 未找到"
        )

    return {"code": 200, "message": "success", "data": bp.to_dict()}


@router.put("/breakpoints/{breakpoint_id}")
async def update_breakpoint(breakpoint_id: str, req: BreakpointRequest):
    """更新断点"""
    success = breakpoint_manager.update_breakpoint(
        breakpoint_id=breakpoint_id,
        condition=req.condition,
        enabled=req.enabled,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"断点 {breakpoint_id} 未找到"
        )

    bp = breakpoint_manager.get_breakpoint(breakpoint_id)
    return {"code": 200, "message": "success", "data": bp.to_dict()}


@router.get("/traces")
async def get_all_traces():
    """获取所有执行轨迹列表"""
    traces = state_visualizer.get_all_traces()
    return {"code": 200, "message": "success", "data": traces}


@router.delete("/trace/{execution_id}")
async def delete_trace(execution_id: str):
    """删除执行轨迹"""
    state_visualizer.remove_trace(execution_id)
    return {"code": 200, "message": "success", "data": {"execution_id": execution_id}}
