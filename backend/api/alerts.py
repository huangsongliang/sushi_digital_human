"""告警管理 API 路由"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from backend.monitoring import (
    AlertLevel,
    AlertStatus,
    ComparisonOperator,
    NotificationChannel,
    get_alert_manager,
    get_notification_gateway,
    get_rule_engine,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["告警管理"])


class RuleCreateRequest(BaseModel):
    """创建规则请求"""

    name: str
    description: str
    metric_name: str
    operator: str
    threshold: float
    alert_level: str
    window_seconds: int = 300
    cooldown_seconds: int = 300


class NotificationConfigRequest(BaseModel):
    """通知配置请求"""

    channel: str
    config: dict


class AlertAcknowledgeRequest(BaseModel):
    """告警确认请求"""

    user_id: str


class AlertCreateRequest(BaseModel):
    """手动创建告警请求"""

    title: str
    description: str
    level: str
    metadata: Optional[dict] = None


class AlertQueryRequest(BaseModel):
    """告警查询请求"""

    level: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100


def get_current_user_id(request: Request) -> str:
    """获取当前用户ID"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未认证")
    return user_id


@router.post("/rules")
async def create_rule(request: RuleCreateRequest):
    """创建告警规则"""
    try:
        rule_engine = get_rule_engine()

        rule = rule_engine.create_threshold_rule(
            name=request.name,
            metric_name=request.metric_name,
            operator=ComparisonOperator(request.operator),
            threshold=request.threshold,
            alert_level=AlertLevel(request.alert_level),
            description=request.description,
            window_seconds=request.window_seconds,
            cooldown_seconds=request.cooldown_seconds,
        )

        return {
            "status": "success",
            "rule_id": rule.id,
            "message": "规则创建成功",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建规则失败: {str(e)}")


@router.get("/rules")
async def list_rules():
    """获取所有规则"""
    try:
        rule_engine = get_rule_engine()
        rules = rule_engine.get_all_rules()

        return {
            "rules": [
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "rule_type": rule.rule_type.value,
                    "alert_level": rule.alert_level.value,
                    "enabled": rule.enabled,
                    "trigger_count": rule.trigger_count,
                    "last_triggered_at": rule.last_triggered_at,
                }
                for rule in rules
            ],
            "count": len(rules),
        }

    except Exception as e:
        logger.error(f"获取规则列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取规则列表失败: {str(e)}")


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """获取规则详情"""
    try:
        rule_engine = get_rule_engine()
        rule = rule_engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="规则不存在")

        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "rule_type": rule.rule_type.value,
            "conditions": [
                {
                    "metric_name": cond.metric_name,
                    "operator": cond.operator.value,
                    "threshold": cond.threshold,
                    "window_seconds": cond.window_seconds,
                }
                for cond in rule.conditions
            ],
            "alert_level": rule.alert_level.value,
            "enabled": rule.enabled,
            "cooldown_seconds": rule.cooldown_seconds,
            "trigger_count": rule.trigger_count,
            "last_triggered_at": rule.last_triggered_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取规则详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取规则详情失败: {str(e)}")


@router.put("/rules/{rule_id}/enable")
async def enable_rule(rule_id: str):
    """启用规则"""
    try:
        rule_engine = get_rule_engine()

        if rule_engine.enable_rule(rule_id):
            return {"status": "success", "message": "规则已启用"}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启用规则失败: {str(e)}")


@router.put("/rules/{rule_id}/disable")
async def disable_rule(rule_id: str):
    """禁用规则"""
    try:
        rule_engine = get_rule_engine()

        if rule_engine.disable_rule(rule_id):
            return {"status": "success", "message": "规则已禁用"}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"禁用规则失败: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """删除规则"""
    try:
        rule_engine = get_rule_engine()

        if rule_engine.remove_rule(rule_id):
            return {"status": "success", "message": "规则已删除"}
        else:
            raise HTTPException(status_code=404, detail="规则不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除规则失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除规则失败: {str(e)}")


@router.get("/rules/statistics")
async def get_rule_statistics():
    """获取规则统计"""
    try:
        rule_engine = get_rule_engine()
        stats = rule_engine.get_rule_statistics()

        return stats

    except Exception as e:
        logger.error(f"获取规则统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取规则统计失败: {str(e)}")


@router.get("/active")
async def get_active_alerts(
    level: Optional[str] = Query(None, description="告警级别"),
    status: Optional[str] = Query(None, description="告警状态"),
):
    """获取活跃告警"""
    try:
        alert_manager = get_alert_manager()

        alerts = alert_manager.get_active_alerts(
            level=AlertLevel(level) if level else None,
            status=AlertStatus(status) if status else None,
        )

        return {
            "alerts": [
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "level": alert.level.value,
                    "title": alert.title,
                    "description": alert.description,
                    "status": alert.status.value,
                    "triggered_at": alert.triggered_at,
                    "acknowledged_by": alert.acknowledged_by,
                }
                for alert in alerts
            ],
            "count": len(alerts),
        }

    except Exception as e:
        logger.error(f"获取活跃告警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取活跃告警失败: {str(e)}")


@router.get("/history")
async def get_alert_history(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
):
    """获取告警历史"""
    try:
        alert_manager = get_alert_manager()

        alerts = alert_manager.get_alert_history(
            limit=limit,
            level=AlertLevel(level) if level else None,
        )

        return {
            "alerts": [
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "level": alert.level.value,
                    "title": alert.title,
                    "description": alert.description,
                    "status": alert.status.value,
                    "triggered_at": alert.triggered_at,
                    "acknowledged_at": alert.acknowledged_at,
                    "resolved_at": alert.resolved_at,
                }
                for alert in alerts
            ],
            "count": len(alerts),
        }

    except Exception as e:
        logger.error(f"获取告警历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """确认告警"""
    try:
        alert_manager = get_alert_manager()

        if alert_manager.acknowledge_alert(alert_id, current_user_id):
            return {"status": "success", "message": "告警已确认"}
        else:
            raise HTTPException(status_code=404, detail="告警不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"确认告警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"确认告警失败: {str(e)}")


@router.post("/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """解决告警"""
    try:
        alert_manager = get_alert_manager()

        if alert_manager.resolve_alert(alert_id):
            return {"status": "success", "message": "告警已解决"}
        else:
            raise HTTPException(status_code=404, detail="告警不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解决告警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解决告警失败: {str(e)}")


@router.get("/statistics")
async def get_alert_statistics():
    """获取告警统计"""
    try:
        alert_manager = get_alert_manager()
        stats = alert_manager.get_alert_statistics()

        return stats

    except Exception as e:
        logger.error(f"获取告警统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取告警统计失败: {str(e)}")


@router.post("/manual")
async def create_manual_alert(request: AlertCreateRequest):
    """手动创建告警"""
    try:
        alert_manager = get_alert_manager()

        alert = alert_manager.create_alert(
            title=request.title,
            description=request.description,
            level=AlertLevel(request.level),
            metadata=request.metadata,
        )

        return {
            "status": "success",
            "alert_id": alert.id,
            "message": "告警创建成功",
        }

    except Exception as e:
        logger.error(f"创建手动告警失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建手动告警失败: {str(e)}")


@router.post("/notification/configure")
async def configure_notification_channel(request: NotificationConfigRequest):
    """配置通知渠道"""
    try:
        gateway = get_notification_gateway()

        channel = NotificationChannel(request.channel)
        gateway.configure_channel(channel, request.config)

        return {
            "status": "success",
            "message": f"通知渠道 {request.channel} 配置成功",
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的通知渠道")
    except Exception as e:
        logger.error(f"配置通知渠道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"配置通知渠道失败: {str(e)}")


@router.get("/notification/channels")
async def list_notification_channels():
    """列出已配置的通知渠道"""
    try:
        gateway = get_notification_gateway()
        channels = gateway.list_configured_channels()

        return {
            "channels": channels,
            "count": len(channels),
        }

    except Exception as e:
        logger.error(f"列出通知渠道失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出通知渠道失败: {str(e)}")


@router.get("/notification/history")
async def get_notification_history(
    limit: int = Query(100, ge=1, le=1000),
    channel: Optional[str] = None,
):
    """获取通知历史"""
    try:
        gateway = get_notification_gateway()

        history = gateway.get_notification_history(
            limit=limit,
            channel=NotificationChannel(channel) if channel else None,
        )

        return {
            "history": history,
            "count": len(history),
        }

    except Exception as e:
        logger.error(f"获取通知历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取通知历史失败: {str(e)}")


@router.get("/operators")
async def get_comparison_operators():
    """获取比较运算符列表"""
    return {"operators": [{"value": op.value, "name": op.name} for op in ComparisonOperator]}


@router.get("/levels")
async def get_alert_levels():
    """获取告警级别列表"""
    return {"levels": [{"value": level.value, "name": level.name} for level in AlertLevel]}
