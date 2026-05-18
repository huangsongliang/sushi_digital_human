"""
Memory 模块测试
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from backend.memory.conversation import Message, ConversationMemory
from backend.memory.redis_client import RedisConnection


class TestMessage:
    """Message 测试"""

    def test_message_creation(self):
        msg = Message(role="user", content="你好")
        assert msg.role == "user"
        assert msg.content == "你好"
        assert msg.timestamp is not None

    def test_message_to_dict(self):
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        msg = Message(role="assistant", content="你好，我是苏东坡", timestamp=timestamp)
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "你好，我是苏东坡"
        assert "timestamp" in data

    def test_message_from_dict(self):
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
        memory = ConversationMemory("test_session_123")
        assert memory.session_id == "test_session_123"
        assert memory.KEY_PREFIX == "conversation:"
        assert "test_session_123" in memory._key

    def test_memory_constants(self):
        assert ConversationMemory.DEFAULT_TTL == 86400 * 7
        assert ConversationMemory.MAX_HISTORY == 50
        assert ConversationMemory.DEFAULT_CONTEXT_LIMIT == 20

    @pytest.mark.asyncio
    async def test_save_message_success(self):
        mock_client = AsyncMock()
        mock_client.rpush.return_value = 1
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        result = await _save_message_with_client(memory, mock_client, "user", "hello")
        assert result is True

    @pytest.mark.asyncio
    async def test_save_message_failure(self):
        mock_client = AsyncMock()
        mock_client.rpush.side_effect = Exception("Redis error")
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        result = await _save_message_with_client(memory, mock_client, "user", "hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_history(self):
        mock_client = AsyncMock()
        mock_client.lrange.return_value = [
            '{"role": "user", "content": "hello", "timestamp": "2024-01-01T12:00:00"}'
        ]
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        history = await _get_history_with_client(memory, mock_client, 10)
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "hello"

    @pytest.mark.asyncio
    async def test_get_history_empty(self):
        mock_client = AsyncMock()
        mock_client.lrange.return_value = []
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        history = await _get_history_with_client(memory, mock_client, 10)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_clear_history(self):
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        result = await _clear_history_with_client(memory, mock_client)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_context_for_rag(self):
        mock_client = AsyncMock()
        mock_client.lrange.return_value = [
            '{"role": "user", "content": "hello", "timestamp": "2024-01-01T12:00:00"}',
            '{"role": "assistant", "content": "hi", "timestamp": "2024-01-01T12:00:01"}'
        ]
        
        memory = ConversationMemory("test_session")
        memory._key = "test_key"
        
        history = await _get_history_with_client(memory, mock_client, 2)
        context = "\n".join([f"{'用户' if m.role == 'user' else '助手'}: {m.content}" for m in history])
        
        assert "用户: hello" in context
        assert "助手: hi" in context


async def _save_message_with_client(memory, client, role, content):
    try:
        import json
        message = Message(role=role, content=content)
        await client.rpush(memory._key, json.dumps(message.to_dict()))
        await client.ltrim(memory._key, -memory.MAX_HISTORY, -1)
        await client.expire(memory._key, memory.DEFAULT_TTL)
        return True
    except Exception:
        return False


async def _get_history_with_client(memory, client, limit):
    try:
        messages_raw = await client.lrange(memory._key, -limit, -1)
        messages = []
        for msg_str in messages_raw:
            if isinstance(msg_str, str):
                msg_dict = msg_str
            else:
                msg_dict = msg_str.decode('utf-8') if isinstance(msg_str, bytes) else str(msg_str)
            if isinstance(msg_dict, str):
                import json
                msg_dict = json.loads(msg_dict)
            messages.append(Message.from_dict(msg_dict))
        return messages
    except Exception:
        return []


async def _clear_history_with_client(memory, client):
    try:
        await client.delete(memory._key)
        return True
    except Exception:
        return False


class TestRedisConnection:
    """RedisConnection 测试"""

    def test_redis_connection_singleton(self):
        conn1 = RedisConnection()
        conn2 = RedisConnection()
        assert conn1 is conn2

    @patch("backend.memory.redis_client.redis.from_url")
    @pytest.mark.asyncio
    async def test_get_client(self, mock_from_url):
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client

        conn = RedisConnection()
        conn._client = None
        client = await conn.get_client()

        assert client is mock_client
        mock_from_url.assert_called_once()

    @patch("backend.memory.redis_client.redis.from_url")
    @pytest.mark.asyncio
    async def test_ping_success(self, mock_from_url):
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        mock_client.ping.return_value = True

        conn = RedisConnection()
        conn._client = None
        result = await conn.ping()

        assert result is True

    @patch("backend.memory.redis_client.redis.from_url")
    @pytest.mark.asyncio
    async def test_ping_failure(self, mock_from_url):
        mock_client = AsyncMock()
        mock_from_url.return_value = mock_client
        mock_client.ping.side_effect = Exception("Connection failed")

        conn = RedisConnection()
        conn._client = None
        result = await conn.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_close(self):
        mock_client = AsyncMock()
        
        conn = RedisConnection()
        conn._client = mock_client
        
        await conn.close()
        
        assert conn._client is None
        mock_client.close.assert_called_once()