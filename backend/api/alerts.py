"""
告警管理 API 路由
提供告警查询、管理和配置功能
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from backend.utils.alerting import AlertRule, AlertSeverity, AlertStatus, alert_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["告警管理"])


@router.get("/summary", summary="获取告警摘要")
async def get_alert_summary():
    """获取告警系统摘要信息"""
    summary = alert_manager.get_alert_summary()
    return {"status": "success", "data": summary}


@router.get("/active", summary="获取活跃告警列表")
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="按告警级别过滤"),
    limit: int = Query(100, ge=1, le=500),
):
    """获取当前活跃的告警列表"""
    alerts = alert_manager.get_active_alerts()

    # 按级别过滤
    if severity:
        try:
            severity_enum = AlertSeverity.from_string(severity)
            alerts = [a for a in alerts if a.severity == severity_enum]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的告警级别: {severity}")

    # 转换为字典格式
    result = []
    for alert in alerts[:limit]:
        result.append(
            {
                "instance_id": alert.instance_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status.value,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            }
        )

    return {"status": "success", "data": result}


@router.get("/history", summary="获取告警历史")
async def get_alert_history(
    limit: int = Query(100, ge=1, le=500),
    start_time: Optional[str] = Query(None, description="开始时间"),
    end_time: Optional[str] = Query(None, description="结束时间"),
):
    """获取告警历史记录"""
    history = alert_manager.get_alert_history(limit)

    # 按时间过滤
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            history = [h for h in history if h.timestamp >= start_dt]
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的开始时间格式")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time)
            history = [h for h in history if h.timestamp <= end_dt]
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的结束时间格式")

    # 转换为字典格式
    result = []
    for alert in history:
        result.append(
            {
                "instance_id": alert.instance_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat(),
                "status": alert.status.value,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            }
        )

    return {"status": "success", "data": result}


@router.post("/{alert_id}/acknowledge", summary="确认告警")
async def acknowledge_alert(alert_id: str, user: Optional[str] = Body(None, embed=True)):
    """确认告警（标记为已处理）"""
    alert_manager.acknowledge_alert(alert_id, user or "system")
    return {"status": "success", "message": f"告警 {alert_id} 已确认"}


@router.post("/{alert_id}/resolve", summary="解决告警")
async def resolve_alert(alert_id: str):
    """解决告警（标记为已解决）"""
    alert_manager.resolve_alert(alert_id)
    return {"status": "success", "message": f"告警 {alert_id} 已解决"}


@router.get("/rules", summary="获取告警规则列表")
async def get_alert_rules():
    """获取所有已注册的告警规则"""
    rules = alert_manager.get_rules()

    result = []
    for rule in rules:
        result.append(
            {
                "name": rule.name,
                "description": rule.description,
                "severity": rule.severity.value,
                "metric_type": rule.metric_type,
                "operator": rule.operator,
                "threshold": rule.threshold,
                "window_seconds": rule.window_seconds,
                "cooldown_seconds": rule.cooldown_seconds,
                "enabled": rule.enabled,
                "notification_channels": rule.notification_channels,
            }
        )

    return {"status": "success", "data": result}


@router.get("/rules/{rule_name}", summary="获取单个告警规则")
async def get_alert_rule(rule_name: str):
    """获取指定的告警规则详情"""
    rule = alert_manager.get_rule(rule_name)
    if not rule:
        raise HTTPException(status_code=404, detail=f"告警规则不存在: {rule_name}")

    return {
        "status": "success",
        "data": {
            "name": rule.name,
            "description": rule.description,
            "severity": rule.severity.value,
            "metric_type": rule.metric_type,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "window_seconds": rule.window_seconds,
            "cooldown_seconds": rule.cooldown_seconds,
            "enabled": rule.enabled,
            "notification_channels": rule.notification_channels,
        },
    }


@router.post("/rules", summary="创建告警规则")
async def create_alert_rule(
    name: str = Body(..., description="规则名称"),
    description: str = Body("", description="规则描述"),
    severity: str = Body(..., description="告警级别"),
    metric_type: str = Body(..., description="指标类型"),
    operator: str = Body(..., description="比较操作符"),
    threshold: float = Body(..., description="阈值"),
    window_seconds: int = Body(60, description="时间窗口（秒）"),
    cooldown_seconds: int = Body(300, description="冷却时间（秒）"),
    enabled: bool = Body(True, description="是否启用"),
    notification_channels: List[str] = Body(["log"], description="通知通道"),
):
    """创建新的告警规则"""
    # 验证告警级别
    try:
        severity_enum = AlertSeverity.from_string(severity)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的告警级别: {severity}")

    # 验证操作符
    valid_operators = [">", "<", ">=", "<=", "=="]
    if operator not in valid_operators:
        raise HTTPException(status_code=400, detail=f"无效的操作符: {operator}，必须是 {valid_operators} 之一")

    # 创建规则
    rule = AlertRule(
        name=name,
        description=description,
        severity=severity_enum,
        metric_type=metric_type,
        operator=operator,
        threshold=threshold,
        window_seconds=window_seconds,
        cooldown_seconds=cooldown_seconds,
        enabled=enabled,
        notification_channels=notification_channels,
    )

    alert_manager.register_rule(rule)

    return {"status": "success", "message": f"告警规则 {name} 已创建"}


@router.put("/rules/{rule_name}", summary="更新告警规则")
async def update_alert_rule(
    rule_name: str,
    description: Optional[str] = Body(None, description="规则描述"),
    severity: Optional[str] = Body(None, description="告警级别"),
    metric_type: Optional[str] = Body(None, description="指标类型"),
    operator: Optional[str] = Body(None, description="比较操作符"),
    threshold: Optional[float] = Body(None, description="阈值"),
    window_seconds: Optional[int] = Body(None, description="时间窗口（秒）"),
    cooldown_seconds: Optional[int] = Body(None, description="冷却时间（秒）"),
    enabled: Optional[bool] = Body(None, description="是否启用"),
    notification_channels: Optional[List[str]] = Body(None, description="通知通道"),
):
    """更新已有的告警规则"""
    rule = alert_manager.get_rule(rule_name)
    if not rule:
        raise HTTPException(status_code=404, detail=f"告警规则不存在: {rule_name}")

    # 更新字段
    if description is not None:
        rule.description = description

    if severity is not None:
        try:
            rule.severity = AlertSeverity.from_string(severity)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的告警级别: {severity}")

    if metric_type is not None:
        rule.metric_type = metric_type

    if operator is not None:
        valid_operators = [">", "<", ">=", "<=", "=="]
        if operator not in valid_operators:
            raise HTTPException(status_code=400, detail=f"无效的操作符: {operator}")
        rule.operator = operator

    if threshold is not None:
        rule.threshold = threshold

    if window_seconds is not None:
        rule.window_seconds = window_seconds

    if cooldown_seconds is not None:
        rule.cooldown_seconds = cooldown_seconds

    if enabled is not None:
        rule.enabled = enabled

    if notification_channels is not None:
        rule.notification_channels = notification_channels

    return {"status": "success", "message": f"告警规则 {rule_name} 已更新"}


@router.delete("/rules/{rule_name}", summary="删除告警规则")
async def delete_alert_rule(rule_name: str):
    """删除告警规则"""
    rule = alert_manager.get_rule(rule_name)
    if not rule:
        raise HTTPException(status_code=404, detail=f"告警规则不存在: {rule_name}")

    alert_manager.unregister_rule(rule_name)

    return {"status": "success", "message": f"告警规则 {rule_name} 已删除"}


@router.post("/trigger", summary="手动触发告警")
async def manual_trigger_alert(
    rule_name: str = Body(..., description="规则名称"),
    message: str = Body(..., description="告警消息"),
    details: Dict[str, Any] = Body(None, description="额外详情"),
):
    """手动触发告警"""
    from backend.utils.alerting import trigger_alert

    trigger_alert(rule_name, message, details)

    return {"status": "success", "message": f"告警 {rule_name} 已触发"}
