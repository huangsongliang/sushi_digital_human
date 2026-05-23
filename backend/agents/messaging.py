"""消息传递模块

负责Agent间的消息传递、消息队列系统和消息持久化。
"""

import asyncio
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MessageType(str, Enum):
    """消息类型枚举"""

    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    TASK_FAILURE = "task_failure"
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    STATUS_UPDATE = "status_update"
    COORDINATION = "coordination"
    ERROR = "error"


class AgentMessage(BaseModel):
    """Agent消息数据模型"""

    id: str = Field(default_factory=lambda: str(uuid4()), description="消息唯一标识")
    sender_id: str = Field(..., description="发送者Agent ID")
    receiver_id: str = Field(..., description="接收者Agent ID")
    message_type: MessageType = Field(..., description="消息类型")
    content: Dict[str, Any] = Field(default_factory=dict, description="消息内容")
    timestamp: float = Field(default_factory=lambda: time.time(), description="发送时间戳")
    correlation_id: Optional[str] = Field(default=None, description="关联ID，用于请求-响应配对")
    priority: int = Field(default=0, description="消息优先级(0-10)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "msg-abc123",
                "sender_id": "agent-doc-retrieval",
                "receiver_id": "agent-summarizer",
                "message_type": "data_response",
                "content": {"documents": [...], "query": "用户问题"},
                "timestamp": 1704067200.0,
                "correlation_id": "req-xyz789",
                "priority": 5,
            }
        }
    }


class MessageQueue:
    """消息队列系统"""

    def __init__(self, redis_url: Optional[str] = None):
        self._queues: Dict[str, asyncio.Queue[AgentMessage]] = {}
        self._subscriptions: Dict[str, Set[str]] = {}
        self._redis_client = None
        self._persistence_enabled = False
        self._processing_tasks: Set[str] = set()

    async def initialize(self, enable_persistence: bool = False):
        """初始化消息队列

        Args:
            enable_persistence: 是否启用消息持久化
        """
        self._persistence_enabled = enable_persistence

        if enable_persistence:
            try:
                self._redis_client = await redis_conn.get_client()
                logger.info("消息队列持久化已启用")
            except Exception as e:
                logger.warning(f"无法连接Redis，持久化已禁用: {str(e)}")
                self._persistence_enabled = False

    async def send_message(self, message: AgentMessage):
        """发送消息到指定接收者

        Args:
            message: 消息对象
        """
        logger.debug(f"发送消息: {message.id} -> {message.receiver_id}")

        if message.receiver_id in self._queues:
            await self._queues[message.receiver_id].put(message)

        if message.receiver_id in self._subscriptions:
            for subscriber in self._subscriptions[message.receiver_id]:
                if subscriber in self._queues:
                    await self._queues[subscriber].put(message)

        if self._persistence_enabled and self._redis_client:
            await self._persist_message(message)

    async def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """从队列接收消息

        Args:
            agent_id: Agent ID
            timeout: 超时时间（秒）

        Returns:
            接收到的消息，如果超时返回None
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()

        try:
            if timeout is None:
                message = await self._queues[agent_id].get()
            else:
                message = await asyncio.wait_for(
                    self._queues[agent_id].get(),
                    timeout=timeout,
                )

            logger.debug(f"接收消息: {message.id} <- {message.sender_id}")
            return message

        except asyncio.TimeoutError:
            return None

    async def broadcast_message(self, message: AgentMessage):
        """广播消息到所有订阅者

        Args:
            message: 消息对象（receiver_id会被忽略）
        """
        logger.debug(f"广播消息: {message.id}")

        for queue_id in self._queues:
            broadcast_msg = message.model_copy()
            broadcast_msg.receiver_id = queue_id
            await self._queues[queue_id].put(broadcast_msg)

        if self._persistence_enabled and self._redis_client:
            await self._persist_message(message)

    def subscribe(self, subscriber_id: str, target_agent_id: str):
        """订阅指定Agent的消息

        Args:
            subscriber_id: 订阅者ID
            target_agent_id: 目标Agent ID
        """
        if target_agent_id not in self._subscriptions:
            self._subscriptions[target_agent_id] = set()

        self._subscriptions[target_agent_id].add(subscriber_id)
        logger.info(f"订阅: {subscriber_id} -> {target_agent_id}")

    def unsubscribe(self, subscriber_id: str, target_agent_id: str):
        """取消订阅

        Args:
            subscriber_id: 订阅者ID
            target_agent_id: 目标Agent ID
        """
        if target_agent_id in self._subscriptions:
            self._subscriptions[target_agent_id].discard(subscriber_id)
            logger.info(f"取消订阅: {subscriber_id} -> {target_agent_id}")

    def create_queue(self, agent_id: str):
        """为Agent创建消息队列

        Args:
            agent_id: Agent ID
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            logger.debug(f"创建队列: {agent_id}")

    def delete_queue(self, agent_id: str):
        """删除Agent的消息队列

        Args:
            agent_id: Agent ID
        """
        if agent_id in self._queues:
            del self._queues[agent_id]
            logger.debug(f"删除队列: {agent_id}")

    async def request_response(
        self,
        message: AgentMessage,
        timeout: float = 30.0,
    ) -> Optional[AgentMessage]:
        """发送请求并等待响应（请求-响应模式）

        Args:
            message: 请求消息
            timeout: 超时时间

        Returns:
            响应消息，如果超时返回None
        """
        if not message.correlation_id:
            message.correlation_id = str(uuid4())

        response_future = asyncio.Future()
        response_handler = None

        async def wait_for_response():
            nonlocal response_handler

            def handler(msg: AgentMessage):
                if msg.correlation_id == message.correlation_id:
                    response_future.set_result(msg)

            response_handler = handler
            self.register_message_handler(message.receiver_id, handler)

            await self.send_message(message)

            try:
                return await asyncio.wait_for(response_future, timeout=timeout)
            finally:
                if response_handler:
                    self.unregister_message_handler(message.receiver_id, handler)

        return await wait_for_response()

    def register_message_handler(self, agent_id: str, handler):
        """注册消息处理器（预留接口）

        Args:
            agent_id: Agent ID
            handler: 消息处理函数
        """

    def unregister_message_handler(self, agent_id: str, handler):
        """取消注册消息处理器（预留接口）

        Args:
            agent_id: Agent ID
            handler: 消息处理函数
        """

    async def _persist_message(self, message: AgentMessage):
        """持久化消息到Redis

        Args:
            message: 消息对象
        """
        try:
            if self._redis_client:
                message_key = f"message:{message.id}"
                message_data = message.model_dump_json()

                await self._redis_client.set(message_key, message_data)
                await self._redis_client.expire(message_key, 86400)

                queue_key = f"queue:{message.receiver_id}"
                await self._redis_client.rpush(queue_key, message.id)

                logger.debug(f"消息已持久化: {message.id}")
        except Exception as e:
            logger.error(f"消息持久化失败: {str(e)}")

    async def load_persisted_messages(self, agent_id: str) -> List[AgentMessage]:
        """加载持久化的消息

        Args:
            agent_id: Agent ID

        Returns:
            消息列表
        """
        messages = []

        if self._persistence_enabled and self._redis_client:
            try:
                queue_key = f"queue:{agent_id}"
                message_ids = await self._redis_client.lrange(queue_key, 0, -1)

                for msg_id in message_ids:
                    message_key = f"message:{msg_id.decode('utf-8')}"
                    message_data = await self._redis_client.get(message_key)

                    if message_data:
                        message = AgentMessage.model_validate_json(message_data)
                        messages.append(message)

                await self._redis_client.delete(queue_key)
                logger.info(f"从持久化加载 {len(messages)} 条消息")
            except Exception as e:
                logger.error(f"加载持久化消息失败: {str(e)}")

        return messages

    def get_queue_size(self, agent_id: str) -> int:
        """获取队列消息数量

        Args:
            agent_id: Agent ID

        Returns:
            队列中的消息数量
        """
        queue = self._queues.get(agent_id)
        return queue.qsize() if queue else 0

    async def clear_queue(self, agent_id: str):
        """清空队列

        Args:
            agent_id: Agent ID
        """
        queue = self._queues.get(agent_id)
        if queue:
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.debug(f"队列已清空: {agent_id}")


# 全局消息队列实例
message_queue = MessageQueue()
