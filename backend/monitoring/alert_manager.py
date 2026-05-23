"""告警管理器
管理告警生命周期：触发、聚合、去重、升级、历史记录
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.monitoring.metrics_collector import get_metrics_collector
from backend.monitoring.notification_gateway import (
    NotificationGateway,
    NotificationMessage,
    NotificationChannel,
    get_notification_gateway,
)
from backend.monitoring.rule_engine import AlertLevel, AlertRule, RuleEngine, get_rule_engine
from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AlertStatus(str, Enum):
    """告警状态"""

    PENDING = "pending"
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class Alert:
    """告警实例"""

    id: str
    rule_id: str
    rule_name: str
    level: AlertLevel
    title: str
    description: str
    status: AlertStatus = AlertStatus.PENDING
    triggered_at: float = 0
    acknowledged_at: float = 0
    resolved_at: float = 0
    acknowledged_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 5000
        self.metrics_collector = get_metrics_collector()
        self.rule_engine = get_rule_engine()
        self.notification_gateway = get_notification_gateway()
        self.evaluation_task: Optional[asyncio.Task] = None
        self.running = False

    async def start(self):
        """启动告警管理器"""
        if self.running:
            return

        self.running = True
        self.evaluation_task = asyncio.create_task(self._evaluation_loop())
        logger.info("告警管理器已启动")

    async def stop(self):
        """停止告警管理器"""
        self.running = False
        if self.evaluation_task:
            self.evaluation_task.cancel()
            try:
                await self.evaluation_task
            except asyncio.CancelledError:
                pass
        logger.info("告警管理器已停止")

    async def _evaluation_loop(self):
        """评估循环"""
        while self.running:
            try:
                await self._evaluate_rules()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"评估循环异常: {str(e)}")
                await asyncio.sleep(10)

    async def _evaluate_rules(self):
        """评估规则"""
        triggered_rules = self.rule_engine.evaluate_all_rules()

        for rule in triggered_rules:
            alert = self._create_alert_from_rule(rule)
            await self._process_alert(alert)

    def _create_alert_from_rule(self, rule: AlertRule) -> Alert:
        """从规则创建告警"""
        alert = Alert(
            id=str(uuid4()),
            rule_id=rule.id,
            rule_name=rule.name,
            level=rule.alert_level,
            title=f"告警: {rule.name}",
            description=rule.description,
            status=AlertStatus.PENDING,
            triggered_at=datetime.now().timestamp(),
            metadata={
                "trigger_count": rule.trigger_count,
                "last_triggered": rule.last_triggered_at,
            },
        )
        return alert

    async def _process_alert(self, alert: Alert):
        """处理告警"""
        existing_alert = self._find_existing_alert(alert.rule_id)
        if existing_alert and existing_alert.status == AlertStatus.FIRING:
            logger.debug(f"告警已存在，跳过: {alert.rule_name}")
            return

        self.active_alerts[alert.id] = alert
        await self._notify_alert(alert)
        logger.info(f"告警触发: {alert.rule_name}, level={alert.level}")

    def _find_existing_alert(self, rule_id: str) -> Optional[Alert]:
        """查找现有告警"""
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.FIRING:
                return alert
        return None

    async def _notify_alert(self, alert: Alert):
        """通知告警"""
        alert.status = AlertStatus.FIRING

        message = NotificationMessage(
            title=alert.title,
            content=alert.description,
            level=alert.level.value,
            channel=NotificationChannel.DINGTALK,
            metadata={
                "alert_id": alert.id,
                "rule_id": alert.rule_id,
                "triggered_at": alert.triggered_at,
            },
        )

        try:
            results = await self.notification_gateway.send_notification(message)
            logger.info(f"告警通知发送结果: {results}")
        except Exception as e:
            logger.error(f"发送告警通知失败: {str(e)}")

    def acknowledge_alert(self, alert_id: str, user_id: str) -> bool:
        """确认告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now().timestamp()
            alert.acknowledged_by = user_id

            self._save_alert_to_db(alert)
            logger.info(f"告警已确认: {alert_id}, by={user_id}")
            return True
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now().timestamp()

            self.alert_history.append(alert)
            if len(self.alert_history) > self.max_history_size:
                self.alert_history.pop(0)

            del self.active_alerts[alert_id]
            self._save_alert_to_db(alert)
            logger.info(f"告警已解决: {alert_id}")
            return True
        return False

    def get_active_alerts(
        self,
        level: Optional[AlertLevel] = None,
        status: Optional[AlertStatus] = None,
    ) -> List[Alert]:
        """获取活跃告警"""
        alerts = list(self.active_alerts.values())

        if level:
            alerts = [a for a in alerts if a.level == level]
        if status:
            alerts = [a for a in alerts if a.status == status]

        return sorted(alerts, key=lambda x: x.triggered_at, reverse=True)

    def get_alert_history(
        self,
        limit: int = 100,
        level: Optional[AlertLevel] = None,
    ) -> List[Alert]:
        """获取告警历史"""
        history = self.alert_history

        if level:
            history = [a for a in history if a.level == level]

        return sorted(history, key=lambda x: x.triggered_at, reverse=True)[:limit]

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        active = list(self.active_alerts.values())
        history = self.alert_history

        stats = {
            "total_active": len(active),
            "total_history": len(history),
            "by_level": {},
            "by_status": {},
            "today_count": 0,
        }

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

        for alert in active + history:
            level = alert.level.value
            if level not in stats["by_level"]:
                stats["by_level"][level] = {"active": 0, "history": 0}

            if alert.id in self.active_alerts:
                stats["by_level"][level]["active"] += 1
            else:
                stats["by_level"][level]["history"] += 1

            if alert.triggered_at >= today_start:
                stats["today_count"] += 1

        for status in AlertStatus:
            stats["by_status"][status.value] = sum(
                1 for a in active if a.status == status
            )

        return stats

    def _save_alert_to_db(self, alert: Alert):
        """保存告警到数据库"""
        try:
            db.execute(
                """
                INSERT INTO alert_history
                (id, rule_id, rule_name, level, title, description, status,
                 triggered_at, acknowledged_at, resolved_at, acknowledged_by, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                status = %s, acknowledged_at = %s, resolved_at = %s, acknowledged_by = %s
                """,
                (
                    alert.id,
                    alert.rule_id,
                    alert.rule_name,
                    alert.level.value,
                    alert.title,
                    alert.description,
                    alert.status.value,
                    alert.triggered_at,
                    alert.acknowledged_at or None,
                    alert.resolved_at or None,
                    alert.acknowledged_by,
                    str(alert.metadata),
                    alert.status.value,
                    alert.acknowledged_at or None,
                    alert.resolved_at or None,
                    alert.acknowledged_by,
                ),
            )
            db.commit()
        except Exception as e:
            logger.error(f"保存告警到数据库失败: {str(e)}")
            db.rollback()

    def create_alert(
        self,
        title: str,
        description: str,
        level: AlertLevel,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Alert:
        """手动创建告警"""
        alert = Alert(
            id=str(uuid4()),
            rule_id="manual",
            rule_name="手动告警",
            level=level,
            title=title,
            description=description,
            status=AlertStatus.FIRING,
            triggered_at=datetime.now().timestamp(),
            metadata=metadata or {},
        )

        self.active_alerts[alert.id] = alert
        logger.info(f"手动告警创建: {title}, level={level}")
        return alert

    def cleanup_old_alerts(self, max_age_days: int = 30) -> int:
        """清理旧告警"""
        cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)

        original_length = len(self.alert_history)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.triggered_at >= cutoff_time
        ]

        deleted_count = original_length - len(self.alert_history)
        if deleted_count > 0:
            logger.info(f"清理旧告警: 删除 {deleted_count} 条")

        return deleted_count


_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        logger.info("告警管理器已初始化")
    return _alert_manager
