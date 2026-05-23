"""通知 API 路由"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.api.websocket import NotificationWebSocket, manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["通知"])


class NotificationType(str, Enum):
    """通知类型"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DOCUMENT_UPDATE = "document_update"
    SYSTEM_ALERT = "system_alert"
    CHAT_MESSAGE = "chat_message"


class SendNotificationRequest(BaseModel):
    """发送通知请求"""

    user_id: int
    title: str
    content: str
    notification_type: NotificationType = NotificationType.INFO
    metadata: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    """通知响应"""

    id: str
    title: str
    content: str
    type: str
    metadata: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime


def get_current_user_id(request: Request) -> int:
    """获取当前用户ID"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未认证")
    return user_id


_notifications_store: Dict[int, List[Dict[str, Any]]] = {}


def _save_notification(notification: Dict[str, Any]):
    """保存通知到内存存储"""
    user_id = notification["user_id"]
    if user_id not in _notifications_store:
        _notifications_store[user_id] = []
    _notifications_store[user_id].insert(0, notification)
    if len(_notifications_store[user_id]) > 100:
        _notifications_store[user_id] = _notifications_store[user_id][:100]


@router.post("/send")
async def send_notification(
    request: SendNotificationRequest,
):
    """发送通知"""
    try:
        notification_id = str(uuid4())

        notification = {
            "id": notification_id,
            "user_id": request.user_id,
            "title": request.title,
            "content": request.content,
            "type": request.notification_type.value,
            "metadata": request.metadata,
            "is_read": False,
            "created_at": datetime.now(),
        }

        _save_notification(notification)

        logger.info(f"通知已发送: user={request.user_id}, type={request.notification_type}")

        return {"status": "success", "notification_id": notification_id, "message": "通知发送成功"}

    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发送通知失败: {str(e)}")


@router.get("/user/{user_id}")
async def get_user_notifications(
    user_id: int,
    unread_only: bool = Query(False, description="仅返回未读通知"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
):
    """获取用户通知"""
    try:
        notifications = _notifications_store.get(user_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n["is_read"]]

        notifications = notifications[:limit]

        return {
            "user_id": user_id,
            "notifications": notifications,
            "count": len(notifications),
            "total": len(_notifications_store.get(user_id, [])),
        }

    except Exception as e:
        logger.error(f"获取通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取通知失败: {str(e)}")


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user_id: int = Depends(get_current_user_id),
):
    """标记通知为已读"""
    try:
        notifications = _notifications_store.get(user_id, [])

        for notification in notifications:
            if notification["id"] == notification_id:
                notification["is_read"] = True
                return {"status": "success", "message": "标记已读成功"}

        raise HTTPException(status_code=404, detail="通知不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记已读失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"标记已读失败: {str(e)}")


@router.put("/user/{user_id}/read-all")
async def mark_all_notifications_read(
    user_id: int,
):
    """标记所有通知为已读"""
    try:
        notifications = _notifications_store.get(user_id, [])

        for notification in notifications:
            notification["is_read"] = True

        return {"status": "success", "message": "全部标记已读成功", "count": len(notifications)}

    except Exception as e:
        logger.error(f"标记全部已读失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"标记全部已读失败: {str(e)}")


@router.get("/user/{user_id}/unread-count")
async def get_unread_count(
    user_id: int,
):
    """获取未读通知数量"""
    try:
        notifications = _notifications_store.get(user_id, [])
        unread_count = sum(1 for n in notifications if not n["is_read"])

        return {
            "user_id": user_id,
            "unread_count": unread_count,
        }

    except Exception as e:
        logger.error(f"获取未读数量失败: {str(e)}")
        return {
            "user_id": user_id,
            "unread_count": 0,
        }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    user_id: int = Depends(get_current_user_id),
):
    """删除通知"""
    try:
        notifications = _notifications_store.get(user_id, [])

        for i, notification in enumerate(notifications):
            if notification["id"] == notification_id:
                notifications.pop(i)
                return {"status": "success", "message": "删除成功"}

        raise HTTPException(status_code=404, detail="通知不存在")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除通知失败: {str(e)}")


@router.delete("/user/{user_id}/clear")
async def clear_all_notifications(
    user_id: int,
):
    """清空所有通知"""
    try:
        _notifications_store[user_id] = []

        return {"status": "success", "message": "清空成功"}

    except Exception as e:
        logger.error(f"清空通知失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空通知失败: {str(e)}")


@router.get("/types")
async def get_notification_types():
    """获取通知类型列表"""
    return {
        "types": [{"value": t.value, "name": t.name, "description": _get_type_description(t)} for t in NotificationType]
    }


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket 实时通知端点"""
    connection_id = await manager.connect(websocket, user_id)

    try:
        await websocket.send_json(
            {"type": "connected", "message": "WebSocket 连接已建立", "connection_id": connection_id}
        )

        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.startswith("subscribe:"):
                channel = data.split(":", 1)[1]
                await websocket.send_json({"type": "subscribed", "channel": channel})

    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket 连接已断开: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {str(e)}")
        await manager.disconnect(websocket, user_id)


@router.get("/online")
async def get_online_users():
    """获取在线用户列表"""
    return {"online_users": manager.get_online_users(), "count": len(manager.get_online_users())}


@router.get("/online/{user_id}")
async def check_user_online(user_id: int):
    """检查用户是否在线"""
    return {"user_id": user_id, "online": manager.is_user_online(user_id)}


def _get_type_description(notification_type: NotificationType) -> str:
    """获取通知类型描述"""
    descriptions = {
        NotificationType.INFO: "一般信息通知",
        NotificationType.SUCCESS: "成功操作通知",
        NotificationType.WARNING: "警告通知",
        NotificationType.ERROR: "错误通知",
        NotificationType.DOCUMENT_UPDATE: "文档更新通知",
        NotificationType.SYSTEM_ALERT: "系统告警通知",
        NotificationType.CHAT_MESSAGE: "聊天消息通知",
    }
    return descriptions.get(notification_type, "")
