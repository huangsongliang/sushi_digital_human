"""Dify集成模块单元测试"""

from backend.core.dify import DifyTool, DifyMessage, DifyToolCall, DifyIntegration


class TestDifyTool:
    """Dify工具测试"""

    def test_tool_creation(self):
        tool = DifyTool(
            name="search_knowledge",
            description="Search knowledge base",
            parameters=[
                {"name": "query", "type": "string", "description": "Search query"}
            ],
        )
        assert tool.name == "search_knowledge"
        assert tool.tool_type == "function"


class TestDifyMessage:
    """Dify消息测试"""

    def test_message_creation(self):
        message = DifyMessage(role="user", content="Hello")
        assert message.role == "user"
        assert message.content == "Hello"

    def test_message_with_tool_call(self):
        tool_call = {"tool_name": "search", "arguments": {"query": "test"}}
        message = DifyMessage(role="assistant", content="", tool_calls=[tool_call])
        assert message.tool_calls is not None
        assert len(message.tool_calls) == 1


class TestDifyToolCall:
    """Dify工具调用测试"""

    def test_tool_call_creation(self):
        tool_call = DifyToolCall(
            tool_name="search", arguments={"query": "test"}, task_id="task123"
        )
        assert tool_call.tool_name == "search"
        assert tool_call.task_id == "task123"


class TestDifyIntegration:
    """Dify集成管理器测试"""

    def test_integration_creation(self):
        integration = DifyIntegration()
        assert integration is not None
