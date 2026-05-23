"""通知网关模块
支持多种通知渠道：邮件、钉钉、企业微信、Webhook
"""

import asyncio
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationChannel(str, Enum):
    """通知渠道"""

    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    FEISHU = "feishu"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class NotificationMessage:
    """通知消息"""

    title: str
    content: str
    level: str = "info"
    channel: NotificationChannel = NotificationChannel.WEBHOOK
    recipients: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NotificationGateway:
    """通知网关"""

    def __init__(self):
        self.channels: Dict[NotificationChannel, Dict[str, Any]] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

    def configure_channel(self, channel: NotificationChannel, config: Dict[str, Any]) -> bool:
        """配置通知渠道"""
        try:
            self.channels[channel] = config
            logger.info(f"通知渠道配置成功: {channel.value}")
            return True
        except Exception as e:
            logger.error(f"配置通知渠道失败: {str(e)}")
            return False

    async def send_notification(
        self,
        message: NotificationMessage,
    ) -> Dict[str, Any]:
        """发送通知"""
        results = {}

        if message.channel == NotificationChannel.EMAIL:
            results["email"] = await self._send_email(message)
        elif message.channel == NotificationChannel.DINGTALK:
            results["dingtalk"] = await self._send_dingtalk(message)
        elif message.channel == NotificationChannel.WECOM:
            results["wecom"] = await self._send_wecom(message)
        elif message.channel == NotificationChannel.FEISHU:
            results["feishu"] = await self._send_feishu(message)
        elif message.channel == NotificationChannel.WEBHOOK:
            results["webhook"] = await self._send_webhook(message)

        self._record_notification(message, results)

        return results

    def send_notification_sync(
        self,
        message: NotificationMessage,
    ) -> Dict[str, Any]:
        """同步发送通知"""
        return asyncio.run(self.send_notification(message))

    async def _send_email(self, message: NotificationMessage) -> Dict[str, Any]:
        """发送邮件"""
        try:
            email_config = self.channels.get(NotificationChannel.EMAIL, {})
            if not email_config:
                return {"success": False, "error": "邮件渠道未配置"}

            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = email_config.get("sender_email")
            msg["To"] = ", ".join(message.recipients)

            text_part = MIMEText(message.content, "plain", "utf-8")
            html_part = MIMEText(
                f"""
                <html>
                <body>
                    <h2>{message.title}</h2>
                    <p>{message.content}</p>
                    <hr>
                    <p><small>来自智能文档问答系统</small></p>
                </body>
                </html>
                """,
                "html",
                "utf-8",
            )

            msg.attach(text_part)
            msg.attach(html_part)

            with smtplib.SMTP(email_config["smtp_host"], email_config.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(email_config["sender_email"], email_config["sender_password"])
                server.send_message(msg)

            logger.info(f"邮件发送成功: {message.recipients}")
            return {"success": True}

        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_dingtalk(self, message: NotificationMessage) -> Dict[str, Any]:
        """发送钉钉通知"""
        try:
            dingtalk_config = self.channels.get(NotificationChannel.DINGTALK, {})
            if not dingtalk_config:
                return {"success": False, "error": "钉钉渠道未配置"}

            webhook_url = dingtalk_config.get("webhook_url")
            if not webhook_url:
                return {"success": False, "error": "钉钉 Webhook URL 未配置"}

            level_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨",
            }

            content = f"{level_emoji.get(message.level, '📢')} **{message.title}**\n\n{message.content}"

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": message.title,
                    "text": content,
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info("钉钉通知发送成功")
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("errmsg", "Unknown error")}

        except Exception as e:
            logger.error(f"钉钉通知发送失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_wecom(self, message: NotificationMessage) -> Dict[str, Any]:
        """发送企业微信通知"""
        try:
            wecom_config = self.channels.get(NotificationChannel.WECOM, {})
            if not wecom_config:
                return {"success": False, "error": "企业微信渠道未配置"}

            webhook_url = wecom_config.get("webhook_url")
            if not webhook_url:
                return {"success": False, "error": "企业微信 Webhook URL 未配置"}

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {message.title}\n\n{message.content}",
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                result = response.json()

                if result.get("errcode") == 0:
                    logger.info("企业微信通知发送成功")
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("errmsg", "Unknown error")}

        except Exception as e:
            logger.error(f"企业微信通知发送失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_feishu(self, message: NotificationMessage) -> Dict[str, Any]:
        """发送飞书通知"""
        try:
            feishu_config = self.channels.get(NotificationChannel.FEISHU, {})
            if not feishu_config:
                return {"success": False, "error": "飞书渠道未配置"}

            webhook_url = feishu_config.get("webhook_url")
            if not webhook_url:
                return {"success": False, "error": "飞书 Webhook URL 未配置"}

            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": message.title,
                        },
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": message.content,
                            },
                        }
                    ],
                },
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload)
                result = response.json()

                if result.get("code") == 0 or result.get("StatusCode") == 0:
                    logger.info("飞书通知发送成功")
                    return {"success": True}
                else:
                    return {"success": False, "error": result.get("msg", "Unknown error")}

        except Exception as e:
            logger.error(f"飞书通知发送失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _send_webhook(self, message: NotificationMessage) -> Dict[str, Any]:
        """发送 Webhook 通知"""
        try:
            webhook_config = self.channels.get(NotificationChannel.WEBHOOK, {})
            webhook_url = webhook_config.get("url")

            if not webhook_url:
                return {"success": False, "error": "Webhook URL 未配置"}

            payload = {
                "event": "alert",
                "title": message.title,
                "content": message.content,
                "level": message.level,
                "metadata": message.metadata,
                "timestamp": str(uuid4()),
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()

                logger.info("Webhook 通知发送成功")
                return {"success": True, "status_code": response.status_code}

        except Exception as e:
            logger.error(f"Webhook 通知发送失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _record_notification(self, message: NotificationMessage, results: Dict[str, Any]):
        """记录通知历史"""
        record = {
            "id": str(uuid4()),
            "title": message.title,
            "content": message.content,
            "level": message.level,
            "channel": message.channel.value,
            "recipients": message.recipients,
            "results": results,
            "timestamp": str(uuid4()),
        }

        self.notification_history.append(record)
        if len(self.notification_history) > self.max_history_size:
            self.notification_history.pop(0)

    def get_notification_history(
        self,
        limit: int = 100,
        channel: Optional[NotificationChannel] = None,
    ) -> List[Dict[str, Any]]:
        """获取通知历史"""
        history = self.notification_history

        if channel:
            history = [n for n in history if n["channel"] == channel.value]

        return history[-limit:]

    def get_channel_config(self, channel: NotificationChannel) -> Optional[Dict[str, Any]]:
        """获取渠道配置（不包含敏感信息）"""
        config = self.channels.get(channel)
        if config:
            safe_config = config.copy()
            for key in ["sender_password", "api_key", "secret"]:
                if key in safe_config:
                    safe_config[key] = "********"
            return safe_config
        return None

    def list_configured_channels(self) -> List[str]:
        """列出已配置的渠道"""
        return [channel.value for channel in self.channels.keys()]


_notification_gateway: Optional[NotificationGateway] = None


def get_notification_gateway() -> NotificationGateway:
    """获取通知网关实例"""
    global _notification_gateway
    if _notification_gateway is None:
        _notification_gateway = NotificationGateway()
        logger.info("通知网关已初始化")
    return _notification_gateway
