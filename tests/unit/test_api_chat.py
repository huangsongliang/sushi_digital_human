"""API聊天模块单元测试"""
import pytest
from backend.api.chat import (
    ChatRequest,
    ChatResponse,
    AddDocumentsRequest,
    format_error_response
)


class TestChatRequestModel:
    """聊天请求模型测试"""

    def test_chat_request_creation(self):
        request = ChatRequest(message="Hello")
        assert request.message == "Hello"
        assert request.session_id is None
        assert request.use_rag is True
        assert request.top_k == 3

    def test_chat_request_with_session(self):
        request = ChatRequest(
            message="Hello",
            session_id="session123",
            use_rag=False,
            top_k=5
        )
        assert request.session_id == "session123"
        assert request.use_rag is False
        assert request.top_k == 5


class TestChatResponseModel:
    """聊天响应模型测试"""

    def test_chat_response_creation(self):
        response = ChatResponse(
            answer="Hello there!",
            session_id="session123"
        )
        assert response.answer == "Hello there!"
        assert response.session_id == "session123"
        assert response.references == []
        assert response.sources == []

    def test_chat_response_with_references(self):
        response = ChatResponse(
            answer="Answer",
            session_id="session123",
            references=[{"title": "Doc1"}],
            sources=["doc1.txt"]
        )
        assert len(response.references) == 1
        assert len(response.sources) == 1


class TestAddDocumentsRequestModel:
    """添加文档请求模型测试"""

    def test_add_documents_request(self):
        request = AddDocumentsRequest(documents=["doc1", "doc2"])
        assert len(request.documents) == 2


class TestErrorResponse:
    """错误响应格式化测试"""

    def test_format_error_response(self):
        result = format_error_response("TEST_ERROR", "Test error")
        assert "error" in result
        assert "message" in result
        assert result["error"] == "TEST_ERROR"
        assert result["message"] == "Test error"

    def test_format_error_response_with_detail(self):
        result = format_error_response("ERROR", "Message", "Detail")
        assert result["detail"] == "Detail"
