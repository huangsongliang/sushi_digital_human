"""
告警系统模块
提供完整的监控告警功能，支持：
- 告警规则定义与管理
- 多级别告警（CRITICAL, ERROR, WARNING, INFO）
- 多种通知方式（日志、邮件、Webhook、钉钉、企业微信）
- 告警抑制与静默机制
- 告警历史记录与查询
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.performance import performance_monitor

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """告警级别枚举"""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @classmethod
    def from_string(cls, value: str) -> "AlertSeverity":
        """从字符串创建告警级别"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.WARNING


class AlertStatus(Enum):
    """告警状态枚举"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """告警规则定义"""

    name: str
    description: str
    severity: AlertSeverity
    metric_type: str  # request_count, latency, error_rate, etc.
    operator: str  # >, <, >=, <=, ==
    threshold: float
    window_seconds: int = 60
    cooldown_seconds: int = 300
    enabled: bool = True
    notification_channels: List[str] = None

    def __post_init__(self):
        if self.notification_channels is None:
            self.notification_channels = ["log"]


@dataclass
class AlertInstance:
    """告警实例"""

    rule_name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    instance_id: str = ""

    def __post_init__(self):
        if not self.instance_id:
            self.instance_id = f"{self.rule_name}-{int(self.timestamp.timestamp())}"


@dataclass
class AlertNotification:
    """告警通知"""

    alert_id: str
    severity: AlertSeverity
    message: str
    channel: str
    sent_at: datetime
    success: bool
    error_message: Optional[str] = None


class AlertManager:
    """告警管理器"""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, AlertInstance] = {}
        self._alert_history: List[AlertInstance] = []
        self._notification_channels: Dict[str, Callable] = {}
        self._cooldown_timestamps: Dict[str, float] = {}
        self._metrics_window: Dict[str, List[float]] = defaultdict(list)
        self._last_check_time: float = time.time()
        self._running = False
        self._check_interval = 10  # 检查间隔（秒）

        # 注册默认通知通道
        self.register_notification_channel("log", self._notify_log)

    def register_rule(self, rule: AlertRule):
        """注册告警规则"""
        self._rules[rule.name] = rule
        logger.info(f"已注册告警规则: {rule.name} (级别: {rule.severity.value})")

    def unregister_rule(self, rule_name: str):
        """注销告警规则"""
        if rule_name in self._rules:
            del self._rules[rule_name]
            logger.info(f"已注销告警规则: {rule_name}")

    def get_rules(self) -> List[AlertRule]:
        """获取所有告警规则"""
        return list(self._rules.values())

    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """获取单个告警规则"""
        return self._rules.get(rule_name)

    def register_notification_channel(self, name: str, handler: Callable):
        """注册通知通道"""
        self._notification_channels[name] = handler
        logger.info(f"已注册通知通道: {name}")

    def get_active_alerts(self) -> List[AlertInstance]:
        """获取所有活跃告警"""
        return list(self._active_alerts.values())

    def get_alert_history(self, limit: int = 100) -> List[AlertInstance]:
        """获取告警历史"""
        return self._alert_history[-limit:]

    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """确认告警"""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self._active_alerts[alert_id].acknowledged_at = datetime.now()
            logger.info(f"告警已确认: {alert_id} by {user}")

    def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now()
            self._alert_history.append(alert)
            del self._active_alerts[alert_id]
            logger.info(f"告警已解决: {alert_id}")

    def _notify_log(self, alert: AlertInstance) -> bool:
        """日志通知通道"""
        try:
            severity_color = {
                AlertSeverity.CRITICAL: "🔴",
                AlertSeverity.ERROR: "🟠",
                AlertSeverity.WARNING: "🟡",
                AlertSeverity.INFO: "🔵",
            }
            logger.error(
                f"{severity_color[alert.severity]} [告警] {alert.rule_name}: {alert.message}"
            )
            return True
        except Exception as e:
            logger.error(f"日志通知失败: {str(e)}")
            return False

    def _notify_webhook(self, alert: AlertInstance, webhook_url: str) -> bool:
        """Webhook 通知通道"""
        try:
            import aiohttp

            async def send_webhook():
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "alert_id": alert.instance_id,
                        "rule_name": alert.rule_name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "details": alert.details,
                        "timestamp": alert.timestamp.isoformat(),
                    }
                    async with session.post(webhook_url, json=payload) as response:
                        return response.status == 200

            asyncio.create_task(send_webhook())
            return True
        except Exception as e:
            logger.error(f"Webhook 通知失败: {str(e)}")
            return False

    def _notify_email(self, alert: AlertInstance, email_config: Dict) -> bool:
        """邮件通知通道"""
        try:
            msg = MIMEMultipart()
            msg["From"] = email_config.get("from", "alerts@example.com")
            msg["To"] = ", ".join(email_config.get("to", []))
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.rule_name}"

            body = f"""
告警信息:
- 规则名称: {alert.rule_name}
- 级别: {alert.severity.value.upper()}
- 消息: {alert.message}
- 时间: {alert.timestamp.isoformat()}
- 详情: {json.dumps(alert.details, ensure_ascii=False, indent=2)}
"""
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(
                email_config.get("smtp_host", "localhost"),
                email_config.get("smtp_port", 587),
            ) as server:
                server.starttls()
                server.login(
                    email_config.get("smtp_user", ""),
                    email_config.get("smtp_password", ""),
                )
                server.send_message(msg)

            return True
        except Exception as e:
            logger.error(f"邮件通知失败: {str(e)}")
            return False

    def _notify_dingtalk(self, alert: AlertInstance, webhook_url: str) -> bool:
        """钉钉机器人通知通道"""
        try:
            import aiohttp
            import hmac
            import hashlib
            import base64

            async def send_dingtalk():
                timestamp = str(round(time.time() * 1000))
                
                # 判断是否需要签名（URL中包含access_token但不包含secret）
                if "secret" in webhook_url.lower():
                    # 解析 secret
                    import urllib.parse
                    parsed = urllib.parse.urlparse(webhook_url)
                    query = urllib.parse.parse_qs(parsed.query)
                    secret = query.get("secret", [""])[0]
                    
                    # 计算签名
                    secret_enc = secret.encode("utf-8")
                    string_to_sign = f"{timestamp}\n{secret}"
                    string_to_sign_enc = string_to_sign.encode("utf-8")
                    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                    
                    # 构建带签名的URL
                    webhook_url = webhook_url + f"&timestamp={timestamp}&sign={sign}"

                async with aiohttp.ClientSession() as session:
                    severity_icon = {
                        AlertSeverity.CRITICAL: "🔴",
                        AlertSeverity.ERROR: "🟠",
                        AlertSeverity.WARNING: "🟡",
                        AlertSeverity.INFO: "🔵",
                    }
                    
                    payload = {
                        "msgtype": "text",
                        "text": {
                            "content": f"{severity_icon[alert.severity]} **[{alert.severity.value.upper()}] {alert.rule_name}**\n\n"
                                        f"📝 消息: {alert.message}\n"
                                        f"🕐 时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                        f"📋 详情: {json.dumps(alert.details, ensure_ascii=False)[:500]}..."
                        }
                    }
                    async with session.post(webhook_url, json=payload) as response:
                        result = await response.json()
                        return result.get("errcode") == 0

            asyncio.create_task(send_dingtalk())
            return True
        except Exception as e:
            logger.error(f"钉钉通知失败: {str(e)}")
            return False

    def _notify_wecom(self, alert: AlertInstance, webhook_url: str) -> bool:
        """企业微信机器人通知通道"""
        try:
            import aiohttp

            async def send_wecom():
                async with aiohttp.ClientSession() as session:
                    severity_color = {
                        AlertSeverity.CRITICAL: "#ff0000",
                        AlertSeverity.ERROR: "#ff6600",
                        AlertSeverity.WARNING: "#ffcc00",
                        AlertSeverity.INFO: "#0066cc",
                    }
                    
                    payload = {
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"## <font color=\"{severity_color[alert.severity]}\">[{alert.severity.value.upper()}] {alert.rule_name}</font>\n\n"
                                        f"> **消息**: {alert.message}\n\n"
                                        f"> **时间**: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                        f"> **详情**: `{json.dumps(alert.details, ensure_ascii=False)[:300]}...`"
                        }
                    }
                    async with session.post(webhook_url, json=payload) as response:
                        result = await response.json()
                        return result.get("errcode") == 0

            asyncio.create_task(send_wecom())
            return True
        except Exception as e:
            logger.error(f"企业微信通知失败: {str(e)}")
            return False

    async def _send_notifications(self, alert: AlertInstance):
        """发送告警通知"""
        rule = self._rules.get(alert.rule_name)
        if not rule:
            return

        for channel in rule.notification_channels:
            if channel == "log":
                self._notify_log(alert)
            elif channel.startswith("webhook:"):
                webhook_url = channel.replace("webhook:", "")
                self._notify_webhook(alert, webhook_url)
            elif channel.startswith("email:"):
                email_config = {}
                self._notify_email(alert, email_config)
            elif channel.startswith("dingtalk:"):
                webhook_url = channel.replace("dingtalk:", "")
                self._notify_dingtalk(alert, webhook_url)
            elif channel.startswith("wecom:"):
                webhook_url = channel.replace("wecom:", "")
                self._notify_wecom(alert, webhook_url)

    def _check_rule(self, rule: AlertRule) -> Optional[AlertInstance]:
        """检查单个规则是否触发告警"""
        if not rule.enabled:
            return None

        # 检查冷却时间
        now = time.time()
        cooldown_key = f"cooldown:{rule.name}"
        last_alert_time = self._cooldown_timestamps.get(cooldown_key, 0)
        if now - last_alert_time < rule.cooldown_seconds:
            return None

        # 获取窗口内的指标数据
        window_data = self._metrics_window.get(rule.metric_type, [])
        if len(window_data) == 0:
            return None

        # 计算指标值
        metric_value = sum(window_data) / len(window_data)

        # 判断是否触发告警
        triggered = False
        if rule.operator == ">":
            triggered = metric_value > rule.threshold
        elif rule.operator == "<":
            triggered = metric_value < rule.threshold
        elif rule.operator == ">=":
            triggered = metric_value >= rule.threshold
        elif rule.operator == "<=":
            triggered = metric_value <= rule.threshold
        elif rule.operator == "==":
            triggered = abs(metric_value - rule.threshold) < 0.001

        if triggered:
            # 更新冷却时间
            self._cooldown_timestamps[cooldown_key] = now

            # 创建告警实例
            alert = AlertInstance(
                rule_name=rule.name,
                severity=rule.severity,
                message=f"指标 {rule.metric_type} {rule.operator} {rule.threshold} (当前值: {metric_value:.2f})",
                details={
                    "metric_type": rule.metric_type,
                    "operator": rule.operator,
                    "threshold": rule.threshold,
                    "current_value": metric_value,
                    "window_size": len(window_data),
                },
                timestamp=datetime.now(),
            )

            # 如果已存在相同告警，更新时间戳
            if alert.instance_id in self._active_alerts:
                self._active_alerts[alert.instance_id].timestamp = alert.timestamp
                self._active_alerts[alert.instance_id].details = alert.details
            else:
                self._active_alerts[alert.instance_id] = alert

            return alert

        return None

    async def _check_all_rules(self):
        """检查所有告警规则"""
        for rule in self._rules.values():
            alert = self._check_rule(rule)
            if alert:
                await self._send_notifications(alert)
                logger.info(f"告警触发: {rule.name}")

    def record_metric(self, metric_type: str, value: float):
        """记录指标数据"""
        now = time.time()

        # 保留窗口内的数据
        window_data = self._metrics_window[metric_type]
        window_data.append(value)

        # 清理过期数据
        min_timestamp = now - 300  # 保留最近5分钟
        while window_data and window_data[0] < min_timestamp:
            window_data.pop(0)

    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_all_rules()
            except Exception as e:
                logger.error(f"告警检查循环异常: {str(e)}")

            await asyncio.sleep(self._check_interval)

    async def start(self):
        """启动告警监控"""
        if self._running:
            return

        self._running = True
        logger.info("告警系统已启动")

        # 启动监控循环
        asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """停止告警监控"""
        self._running = False
        logger.info("告警系统已停止")

    def get_alert_summary(self) -> Dict[str, Any]:
        """获取告警摘要"""
        active_alerts = self.get_active_alerts()
        summary = {
            "active_alerts": len(active_alerts),
            "by_severity": {
                "critical": len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "error": len([a for a in active_alerts if a.severity == AlertSeverity.ERROR]),
                "warning": len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in active_alerts if a.severity == AlertSeverity.INFO]),
            },
            "total_history": len(self._alert_history),
            "rules_count": len(self._rules),
        }
        return summary


# 全局告警管理器实例
alert_manager = AlertManager()


def init_alert_rules():
    """初始化默认告警规则"""
    default_rules = [
        # 高错误率告警
        AlertRule(
            name="high_error_rate",
            description="API 错误率过高",
            severity=AlertSeverity.CRITICAL,
            metric_type="error_rate",
            operator=">",
            threshold=0.1,  # 错误率超过10%
            window_seconds=60,
            cooldown_seconds=300,
        ),
        # 高延迟告警
        AlertRule(
            name="high_latency",
            description="API 响应延迟过高",
            severity=AlertSeverity.WARNING,
            metric_type="avg_latency",
            operator=">",
            threshold=5.0,  # 平均延迟超过5秒
            window_seconds=60,
            cooldown_seconds=120,
        ),
        # 服务不可用告警
        AlertRule(
            name="service_unavailable",
            description="服务健康检查失败",
            severity=AlertSeverity.CRITICAL,
            metric_type="health_status",
            operator="<",
            threshold=1.0,  # 健康状态低于1（不健康）
            window_seconds=30,
            cooldown_seconds=60,
        ),
        # 高并发告警
        AlertRule(
            name="high_concurrency",
            description="并发请求数过高",
            severity=AlertSeverity.WARNING,
            metric_type="concurrency",
            operator=">",
            threshold=100,  # 并发超过100
            window_seconds=10,
            cooldown_seconds=60,
        ),
        # LLM调用失败告警
        AlertRule(
            name="llm_call_failure",
            description="LLM 调用失败率过高",
            severity=AlertSeverity.ERROR,
            metric_type="llm_failure_rate",
            operator=">",
            threshold=0.2,  # 失败率超过20%
            window_seconds=60,
            cooldown_seconds=300,
        ),
    ]

    for rule in default_rules:
        alert_manager.register_rule(rule)


async def start_alerting():
    """启动告警系统"""
    init_alert_rules()
    await alert_manager.start()


async def stop_alerting():
    """停止告警系统"""
    await alert_manager.stop()


def record_alert_metric(metric_type: str, value: float):
    """记录告警指标"""
    alert_manager.record_metric(metric_type, value)


def trigger_alert(rule_name: str, message: str, details: Dict[str, Any] = None):
    """手动触发告警"""
    rule = alert_manager.get_rule(rule_name)
    if not rule:
        logger.warning(f"告警规则不存在: {rule_name}")
        return

    alert = AlertInstance(
        rule_name=rule.name,
        severity=rule.severity,
        message=message,
        details=details or {},
        timestamp=datetime.now(),
    )
    alert_manager._active_alerts[alert.instance_id] = alert

    # 发送通知
    asyncio.create_task(alert_manager._send_notifications(alert))

    logger.info(f"手动告警已触发: {rule_name}")