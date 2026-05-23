"""Webhook 事件驱动系统"""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class WebhookEvent(str, Enum):
    """Webhook 事件类型"""

    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTERED = "user.registered"
    CHAT_MESSAGE = "chat.message"
    PERMISSION_CHANGED = "permission.changed"
    SYSTEM_ALERT = "system.alert"


class WebhookManager:
    """Webhook 管理器"""

    def __init__(self):
        self.subscribers: Dict[WebhookEvent, List[Dict[str, Any]]] = {}
        self.delivery_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def register_webhook(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        enabled: bool = True,
    ) -> str:
        """注册 Webhook"""
        webhook_id = str(uuid4())

        try:
            db.execute(
                """
                INSERT INTO webhooks (id, url, events, secret, headers, enabled, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    webhook_id,
                    url,
                    ",".join([e.value for e in events]),
                    secret,
                    json.dumps(headers) if headers else None,
                    enabled,
                    datetime.now(),
                ),
            )
            db.commit()

            logger.info(f"Webhook 注册成功: {webhook_id} -> {url}")
            return webhook_id

        except Exception as e:
            logger.error(f"注册 Webhook 失败: {str(e)}")
            db.rollback()
            raise

    def unregister_webhook(self, webhook_id: str) -> bool:
        """取消注册 Webhook"""
        try:
            db.execute("DELETE FROM webhooks WHERE id = %s", (webhook_id,))
            db.commit()
            logger.info(f"Webhook 已取消: {webhook_id}")
            return True

        except Exception as e:
            logger.error(f"取消 Webhook 失败: {str(e)}")
            db.rollback()
            return False

    def update_webhook(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[WebhookEvent]] = None,
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        enabled: Optional[bool] = None,
    ) -> bool:
        """更新 Webhook"""
        try:
            updates = []
            params = []

            if url is not None:
                updates.append("url = %s")
                params.append(url)

            if events is not None:
                updates.append("events = %s")
                params.append(",".join([e.value for e in events]))

            if secret is not None:
                updates.append("secret = %s")
                params.append(secret)

            if headers is not None:
                updates.append("headers = %s")
                params.append(json.dumps(headers))

            if enabled is not None:
                updates.append("enabled = %s")
                params.append(enabled)

            if updates:
                params.append(webhook_id)
                db.execute(
                    f"UPDATE webhooks SET {', '.join(updates)} WHERE id = %s",
                    tuple(params),
                )
                db.commit()

            logger.info(f"Webhook 已更新: {webhook_id}")
            return True

        except Exception as e:
            logger.error(f"更新 Webhook 失败: {str(e)}")
            db.rollback()
            return False

    def list_webhooks(self) -> List[Dict[str, Any]]:
        """列出所有 Webhook"""
        try:
            result = db.execute(
                """
                SELECT id, url, events, secret, headers, enabled, created_at, last_triggered_at
                FROM webhooks
                """
            )

            webhooks = []
            for row in result.fetchall():
                webhooks.append(
                    {
                        "id": row[0],
                        "url": row[1],
                        "events": row[2].split(",") if row[2] else [],
                        "secret": bool(row[3]),
                        "headers": json.loads(row[4]) if row[4] else {},
                        "enabled": row[5],
                        "created_at": str(row[6]),
                        "last_triggered_at": str(row[7]) if row[7] else None,
                    }
                )

            return webhooks

        except Exception as e:
            logger.error(f"列出 Webhook 失败: {str(e)}")
            return []

    async def trigger_event(
        self,
        event: WebhookEvent,
        data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """触发 Webhook 事件"""
        try:
            result = db.execute(
                """
                SELECT id, url, secret, headers
                FROM webhooks
                WHERE enabled = %s
                AND events LIKE %s
                """,
                (True, f"%{event.value}%"),
            )

            webhooks = result.fetchall()
            delivery_tasks = []

            for webhook in webhooks:
                webhook_id, url, secret, headers = webhook
                headers_dict = json.loads(headers) if headers else {}

                delivery_tasks.append(
                    self._deliver_webhook(
                        webhook_id=webhook_id,
                        url=url,
                        event=event,
                        data=data,
                        secret=secret,
                        headers=headers_dict,
                        user_id=user_id,
                    )
                )

            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]

        except Exception as e:
            logger.error(f"触发 Webhook 事件失败: {str(e)}")
            return []

    async def _deliver_webhook(
        self,
        webhook_id: str,
        url: str,
        event: WebhookEvent,
        data: Dict[str, Any],
        secret: Optional[str],
        headers: Dict[str, str],
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """交付 Webhook"""
        payload = {
            "event": event.value,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "webhook_id": webhook_id,
        }

        if user_id:
            payload["user_id"] = user_id

        payload_json = json.dumps(payload)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SushiDigitalHuman-Webhook/1.0",
            **headers,
        }

        if secret:
            signature = hmac.new(
                secret.encode(),
                payload_json.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, content=payload_json, headers=headers)

                success = 200 <= response.status_code < 300

                db.execute(
                    """
                    UPDATE webhooks
                    SET last_triggered_at = %s, failure_count = failure_count + %s
                    WHERE id = %s
                    """,
                    (
                        datetime.now(),
                        0 if success else 1,
                        webhook_id,
                    ),
                )
                db.commit()

                return {
                    "webhook_id": webhook_id,
                    "url": url,
                    "status_code": response.status_code,
                    "success": success,
                }

        except Exception as e:
            logger.error(f"交付 Webhook 失败: {webhook_id}: {str(e)}")

            db.execute(
                """
                UPDATE webhooks
                SET last_triggered_at = %s, failure_count = failure_count + 1
                WHERE id = %s
                """,
                (datetime.now(), webhook_id),
            )
            db.commit()

            return {
                "webhook_id": webhook_id,
                "url": url,
                "success": False,
                "error": str(e),
            }

    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """测试 Webhook"""
        try:
            result = db.execute(
                """
                SELECT url, secret, headers FROM webhooks WHERE id = %s
                """,
                (webhook_id,),
            )
            row = result.fetchone()

            if not row:
                return {"success": False, "error": "Webhook 不存在"}

            url, secret, headers = row

            payload = {
                "event": "test",
                "timestamp": datetime.now().isoformat(),
                "message": "This is a test webhook",
                "webhook_id": webhook_id,
            }

            payload_json = json.dumps(payload)
            headers_dict = {
                "Content-Type": "application/json",
                "User-Agent": "SushiDigitalHuman-Webhook-Test/1.0",
            }

            if headers:
                headers_dict.update(json.loads(headers))

            if secret:
                signature = hmac.new(
                    secret.encode(),
                    payload_json.encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers_dict["X-Webhook-Signature"] = signature

            return {
                "webhook_id": webhook_id,
                "url": url,
                "payload": payload,
                "headers": headers_dict,
            }

        except Exception as e:
            logger.error(f"测试 Webhook 失败: {str(e)}")
            return {"success": False, "error": str(e)}


_webhook_manager: Optional[WebhookManager] = None


def get_webhook_manager() -> WebhookManager:
    """获取 Webhook 管理器实例"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
        logger.info("Webhook 管理器已初始化")
    return _webhook_manager
