"""消息通知系统"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationType(str, Enum):
    """通知类型"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DOCUMENT_UPDATE = "document_update"
    SYSTEM_ALERT = "system_alert"
    CHAT_MESSAGE = "chat_message"


class NotificationManager:
    """通知管理器"""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()

    def send_notification(
        self,
        user_id: str,
        title: str,
        content: str,
        notification_type: NotificationType = NotificationType.INFO,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """发送通知"""
        notification_id = str(uuid4())

        try:
            db.execute(
                """
                INSERT INTO notifications
                (id, user_id, title, content, type, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    notification_id,
                    user_id,
                    title,
                    content,
                    notification_type.value,
                    str(metadata) if metadata else None,
                    datetime.now(),
                ),
            )
            db.commit()

            logger.info(f"通知已发送: user={user_id}, type={notification_type}")
            return notification_id

        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}")
            db.rollback()
            raise

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取用户通知"""
        try:
            query = """
                SELECT id, title, content, type, metadata, read, created_at
                FROM notifications
                WHERE user_id = %s
            """
            params = [user_id]

            if unread_only:
                query += " AND read = 0"

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            result = db.execute(query, tuple(params))

            notifications = []
            for row in result.fetchall():
                notifications.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "type": row[3],
                    "metadata": row[4],
                    "read": row[5],
                    "created_at": str(row[6]),
                })

            return notifications

        except Exception as e:
            logger.error(f"获取通知失败: {str(e)}")
            return []

    def mark_as_read(self, notification_id: str) -> bool:
        """标记为已读"""
        try:
            db.execute(
                "UPDATE notifications SET read = 1 WHERE id = %s",
                (notification_id,),
            )
            db.commit()
            return True

        except Exception as e:
            logger.error(f"标记已读失败: {str(e)}")
            return False

    def get_unread_count(self, user_id: str) -> int:
        """获取未读数量"""
        try:
            result = db.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = %s AND read = 0",
                (user_id,),
            )
            return result.fetchone()[0]

        except Exception as e:
            logger.error(f"获取未读数量失败: {str(e)}")
            return 0


_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """获取通知管理器实例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
        logger.info("通知管理器已初始化")
    return _notification_manager
