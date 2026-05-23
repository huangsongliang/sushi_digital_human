"""WebSocket 连接管理器"""

from typing import Dict, List
from uuid import uuid4

from fastapi import WebSocket

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.user_connections: Dict[str, int] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """建立 WebSocket 连接"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)

        connection_id = str(uuid4())
        self.user_connections[connection_id] = user_id

        logger.info(f"WebSocket 连接已建立: user_id={user_id}, connection_id={connection_id}")

        return connection_id

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """断开 WebSocket 连接"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

        for conn_id, uid in list(self.user_connections.items()):
            if uid == user_id:
                del self.user_connections[conn_id]

        logger.info(f"WebSocket 连接已断开: user_id={user_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        """向指定用户发送消息"""
        if user_id in self.active_connections:
            disconnected = []

            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"发送消息失败: {str(e)}")
                    disconnected.append(websocket)

            for ws in disconnected:
                await self.disconnect(ws, user_id)

            logger.info(f"个人消息已发送: user_id={user_id}, message_type={message.get('type')}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接的用户"""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)

        logger.info(f"广播消息已发送: {len(self.active_connections)} 个用户")

    def get_online_users(self) -> List[int]:
        """获取在线用户列表"""
        return list(self.active_connections.keys())

    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0


manager = ConnectionManager()


class NotificationWebSocket:
    """通知 WebSocket 服务"""

    @staticmethod
    async def notify_user(user_id: int, notification: dict):
        """通知用户"""
        message = {"type": "notification", "data": notification}
        await manager.send_personal_message(message, user_id)

    @staticmethod
    async def notify_system(message: str, user_ids: List[int] = None):
        """系统通知"""
        notification = {"type": "system", "message": message}

        if user_ids:
            for user_id in user_ids:
                await manager.send_personal_message(notification, user_id)
        else:
            await manager.broadcast(notification)

    @staticmethod
    async def notify_document_update(user_id: int, document_id: str, action: str):
        """文档更新通知"""
        notification = {"type": "document_update", "document_id": document_id, "action": action}
        await manager.send_personal_message(notification, user_id)

    @staticmethod
    async def notify_error(user_id: int, error_message: str):
        """错误通知"""
        notification = {"type": "error", "message": error_message}
        await manager.send_personal_message(notification, user_id)
