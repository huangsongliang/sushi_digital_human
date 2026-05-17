"""对话记忆模块 - Redis 实现"""
import json
from typing import List, Optional
from datetime import datetime
from backend.memory.redis_client import redis_conn
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class Message:
    """消息模型"""
    
    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class ConversationMemory:
    """对话记忆管理器"""
    
    KEY_PREFIX = "conversation:"
    DEFAULT_TTL = 86400 * 7  # 7 天过期
    MAX_HISTORY = 50  # 最大保留历史消息数
    DEFAULT_CONTEXT_LIMIT = 20  # 默认用于上下文的消息条数
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._key = f"{self.KEY_PREFIX}{session_id}"
    
    async def save_message(self, role: str, content: str) -> bool:
        """保存消息到历史"""
        try:
            client = await redis_conn.get_client()
            message = Message(role=role, content=content)
            await client.rpush(self._key, json.dumps(message.to_dict()))
            
            # 限制历史长度
            await client.ltrim(self._key, -self.MAX_HISTORY, -1)
            
            # 设置过期时间
            await client.expire(self._key, self.DEFAULT_TTL)
            
            logger.info(f"消息已保存: session={self.session_id}, role={role}")
            return True
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False
    
    async def get_history(self, limit: int = 10) -> List[Message]:
        """获取对话历史"""
        try:
            client = await redis_conn.get_client()
            messages_raw = await client.lrange(self._key, -limit, -1)
            
            messages = []
            for msg_str in messages_raw:
                msg_dict = json.loads(msg_str)
                messages.append(Message.from_dict(msg_dict))
            
            logger.info(f"获取历史消息: session={self.session_id}, count={len(messages)}")
            return messages
        except Exception as e:
            logger.error(f"获取历史失败: {e}")
            return []
    
    async def get_full_history(self) -> List[Message]:
        """获取完整对话历史"""
        return await self.get_history(limit=self.MAX_HISTORY)
    
    async def get_recent_history(self, n: int = 5) -> List[Message]:
        """获取最近 N 条消息"""
        return await self.get_history(limit=n)
    
    async def clear_history(self) -> bool:
        """清空对话历史"""
        try:
            client = await redis_conn.get_client()
            await client.delete(self._key)
            logger.info(f"对话历史已清空: session={self.session_id}")
            return True
        except Exception as e:
            logger.error(f"清空历史失败: {e}")
            return False
    
    async def get_context_for_rag(self, max_messages: int = 10) -> str:
        """获取用于 RAG 的上下文"""
        messages = await self.get_recent_history(n=max_messages)
        
        if not messages:
            return ""
        
        context_parts = []
        for msg in messages:
            role_name = "用户" if msg.role == "user" else "助手"
            context_parts.append(f"{role_name}: {msg.content}")
        
        return "\n".join(context_parts)
