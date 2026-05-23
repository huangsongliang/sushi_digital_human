"""追踪管理API

提供追踪相关API端点：
- GET /api/tracing/trace/{trace_id} - 获取追踪详情
- GET /api/tracing/traces - 列出追踪记录
- GET /api/tracing/performance - 性能统计
- GET /api/tracing/errors - 错误列表
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.monitoring.error_tracker import get_error_tracker
from backend.monitoring.performance_monitor import get_performance_monitor
from backend.monitoring.tracing import get_tracing_manager

router = APIRouter(prefix="/api/tracing", tags=["tracing"])


@router.get("/trace/{trace_id}")
async def get_trace_detail(trace_id: str):
    """获取追踪详情

    Args:
        trace_id: 追踪ID

    Returns:
        追踪详情
    """
    tracing_manager = get_tracing_manager()
    trace_spans = tracing_manager.get_trace(trace_id)

    if not trace_spans:
        raise HTTPException(status_code=404, detail="追踪记录不存在")

    return {"trace_id": trace_id, "spans": [span.to_dict() for span in trace_spans]}


@router.get("/traces")
async def list_traces(limit: int = Query(default=100, ge=1, le=1000)):
    """列出追踪记录

    Args:
        limit: 返回数量限制

    Returns:
        追踪记录列表
    """
    tracing_manager = get_tracing_manager()
    traces = tracing_manager.get_recent_traces(limit=limit)

    return {"total": len(traces), "traces": traces}


@router.get("/performance")
async def get_performance_stats(time_window: Optional[int] = Query(default=None, description="时间窗口（分钟）")):
    """获取性能统计

    Args:
        time_window: 时间窗口（分钟）

    Returns:
        性能统计数据
    """
    performance_monitor = get_performance_monitor()
    summary = performance_monitor.get_performance_summary(time_window=time_window)
    bottlenecks = performance_monitor.get_bottlenecks()
    endpoint_stats = performance_monitor.get_endpoint_stats()

    return {"summary": summary, "bottlenecks": bottlenecks, "endpoint_stats": endpoint_stats}


@router.get("/performance/endpoint/{endpoint}")
async def get_endpoint_performance(endpoint: str):
    """获取特定端点的性能统计

    Args:
        endpoint: 端点路径

    Returns:
        端点性能统计
    """
    performance_monitor = get_performance_monitor()
    stats = performance_monitor.get_endpoint_stats(endpoint)

    if not stats:
        raise HTTPException(status_code=404, detail="端点统计不存在")

    return stats


@router.get("/errors")
async def list_errors(
    component: Optional[str] = Query(default=None, description="组件名称过滤"),
    error_type: Optional[str] = Query(default=None, description="错误类型过滤"),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """列出错误记录

    Args:
        component: 组件名称过滤
        error_type: 错误类型过滤
        limit: 返回数量限制

    Returns:
        错误列表
    """
    error_tracker = get_error_tracker()
    errors = error_tracker.get_errors(component=component, error_type=error_type, limit=limit)

    return {"total": len(errors), "errors": errors}


@router.get("/errors/aggregated")
async def get_aggregated_errors(
    min_count: int = Query(default=1, ge=1),
    sort_by: str = Query(default="count", pattern="^(count|frequency|last_occurrence)$"),
):
    """获取聚合后的错误信息

    Args:
        min_count: 最小错误数量
        sort_by: 排序字段

    Returns:
        聚合错误列表
    """
    error_tracker = get_error_tracker()
    aggregations = error_tracker.get_aggregated_errors(min_count=min_count, sort_by=sort_by)

    return {"total": len(aggregations), "aggregations": aggregations}


@router.get("/errors/statistics")
async def get_error_statistics(time_window: Optional[int] = Query(default=None, description="时间窗口（分钟）")):
    """获取错误统计信息

    Args:
        time_window: 时间窗口（分钟）

    Returns:
        错误统计信息
    """
    error_tracker = get_error_tracker()
    statistics = error_tracker.get_error_statistics(time_window=time_window)

    return statistics


@router.get("/errors/{error_id}")
async def get_error_detail(error_id: str):
    """获取错误详情

    Args:
        error_id: 错误ID

    Returns:
        错误详情
    """
    error_tracker = get_error_tracker()
    error_info = error_tracker.get_error(error_id)

    if not error_info:
        raise HTTPException(status_code=404, detail="错误记录不存在")

    return error_info.to_dict()


@router.get("/errors/{error_id}/stacktrace")
async def get_error_stacktrace(error_id: str):
    """获取错误堆栈跟踪

    Args:
        error_id: 错误ID

    Returns:
        堆栈跟踪信息
    """
    error_tracker = get_error_tracker()
    stack_trace = error_tracker.get_stack_trace(error_id)

    if not stack_trace:
        raise HTTPException(status_code=404, detail="堆栈跟踪不存在")

    return {"error_id": error_id, "stack_trace": stack_trace}


@router.get("/performance/request/{request_id}")
async def get_request_trace(request_id: str):
    """获取请求链路可视化数据

    Args:
        request_id: 请求ID

    Returns:
        链路可视化数据
    """
    performance_monitor = get_performance_monitor()
    trace_data = performance_monitor.get_request_trace_data(request_id)

    if not trace_data:
        raise HTTPException(status_code=404, detail="请求记录不存在")

    return trace_data


@router.get("/performance/bottlenecks")
async def get_performance_bottlenecks(severity: Optional[str] = Query(default=None, pattern="^(warning|critical)$")):
    """获取性能瓶颈列表

    Args:
        severity: 严重程度过滤

    Returns:
        瓶颈列表
    """
    performance_monitor = get_performance_monitor()
    bottlenecks = performance_monitor.get_bottlenecks(severity=severity)

    return {"total": len(bottlenecks), "bottlenecks": bottlenecks}


@router.get("/analysis/bottlenecks")
async def analyze_bottlenecks():
    """执行性能瓶颈分析

    Returns:
        瓶颈分析结果
    """
    performance_monitor = get_performance_monitor()
    analysis = performance_monitor.analyze_bottlenecks()

    return {"total": len(analysis), "analysis": analysis}


@router.get("/analysis/errors")
async def analyze_errors():
    """分析错误模式

    Returns:
        错误分析结果
    """
    error_tracker = get_error_tracker()
    analysis = error_tracker.analyze_errors()

    return {"total": len(analysis), "analysis": analysis}
