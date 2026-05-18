"""
Memory 模块测试
"""

import pytest
from datetime import datetime
from backend.memory.conversation import Message, ConversationMemory


class TestMessage:
    """Message 测试"""

    def test_message_creation(self):
        """测试消息创建"""
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        """测试消息转字典"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        msg = Message(role="assistant", content="你好，我是苏东坡", timestamp=timestamp)
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "你好，我是苏东坡"
        assert "timestamp" in data

    def test_message_from_dict(self):
        """测试从字典创建消息"""
        data = {
            "role": "user",
            "content": "测试消息",
            "timestamp": "2024-01-01T12:00:00"
        }
        msg = Message.from_dict(data)
        assert msg.role == "user"
        assert msg.content == "测试消息"
        assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)


class TestConversationMemory:
    """ConversationMemory 测试"""

    def test_memory_creation(self):
        """测试对话记忆创建"""
        memory = ConversationMemory("test_session_123")
        assert memory.session_id == "test_session_123"
        assert memory.KEY_PREFIX == "conversation:"
        assert "test_session_123" in memory._key

    def test_memory_constants(self):
        """测试对话记忆常量"""
        assert ConversationMemory.DEFAULT_TTL == 86400 * 7
        assert ConversationMemory.MAX_HISTORY == 50
        assert ConversationMemory.DEFAULT_CONTEXT_LIMIT == 20
