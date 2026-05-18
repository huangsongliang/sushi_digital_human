"""聊天API单元测试"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.api.chat import (
    ChatRequest,
    ChatResponse,
    AddDocumentsRequest,
    format_error_response
)


class TestChatRequestModel:
    """聊天请求模型测试"""
    
    def test_chat_request_creation(self):
        request = ChatRequest(message="Hello", session_id="test-session", use_rag=True, top_k=3)
        assert request.message == "Hello"
        assert request.session_id == "test-session"
        assert request.use_rag is True
        assert request.top_k == 3
    
    def test_chat_request_defaults(self):
        request = ChatRequest(message="Hello")
        assert request.session_id is None
        assert request.use_rag is True
        assert request.top_k == 3


class TestChatResponseModel:
    """聊天响应模型测试"""
    
    def test_chat_response_creation(self):
        response = ChatResponse(
            answer="Hello",
            session_id="test-session",
            references=[],
            sources=[]
        )
        assert response.answer == "Hello"
        assert response.session_id == "test-session"
        assert response.references == []
        assert response.sources == []


class TestAddDocumentsRequestModel:
    """添加文档请求模型测试"""
    
    def test_add_documents_request(self):
        request = AddDocumentsRequest(documents=["doc1", "doc2"])
        assert request.documents == ["doc1", "doc2"]


class TestErrorResponse:
    """错误响应格式化测试"""
    
    def test_format_error_response(self):
        error = format_error_response("INVALID_INPUT", "错误消息", "详细信息")
        assert error["error"] == "INVALID_INPUT"
        assert error["message"] == "错误消息"
        assert error["detail"] == "详细信息"
        assert "timestamp" in error
        assert "request_id" in error
    
    def test_format_error_response_no_detail(self):
        error = format_error_response("ERROR", "消息")
        assert error["detail"] is None