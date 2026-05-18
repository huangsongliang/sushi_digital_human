"""对话记忆模块单元测试"""
from datetime import datetime
from backend.memory.conversation import Message, ConversationMemory
from backend.memory.redis_client import redis_conn


class TestMessage:
    """消息模型测试"""

    def test_message_creation(self):
        message = Message(
            role="user",
            content="Hello"
        )
        assert message.role == "user"
        assert message.content == "Hello"
        assert isinstance(message.timestamp, datetime)

    def test_message_to_dict(self):
        message = Message(
            role="user",
            content="Hello"
        )
        result = message.to_dict()
        assert result["role"] == "user"
        assert result["content"] == "Hello"
        assert "timestamp" in result

    def test_message_from_dict(self):
        data = {
            "role": "assistant",
            "content": "Hi there",
            "timestamp": "2024-01-01T00:00:00"
        }
        message = Message.from_dict(data)
        assert message.role == "assistant"
        assert message.content == "Hi there"


class TestConversationMemory:
    """对话记忆测试"""

    def test_memory_creation(self):
        memory = ConversationMemory("session123")
        assert memory is not None
        assert memory.session_id == "session123"


class TestRedisConnection:
    """Redis连接测试"""

    def test_redis_connection_singleton(self):
        conn1 = redis_conn
        conn2 = redis_conn
        assert conn1 is conn2
