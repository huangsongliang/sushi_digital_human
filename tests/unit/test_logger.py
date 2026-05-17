"""日志模块单元测试"""

import pytest
from backend.utils.logger import (
    set_request_id,
    get_request_id,
    set_session_id,
    get_session_id,
    with_request_context,
    StructuredLogger,
    json_formatter
)


class TestRequestTracking:
    """请求追踪测试"""
    
    def test_set_get_request_id(self):
        """测试设置和获取请求 ID"""
        request_id = set_request_id()
        assert request_id is not None
        assert len(request_id) > 0
        assert get_request_id() == request_id
    
    def test_set_get_session_id(self):
        """测试设置和获取会话 ID"""
        session_id = "test-session-123"
        set_session_id(session_id)
        assert get_session_id() == session_id
    
    def test_request_context_manager(self):
        """测试请求上下文管理器"""
        # 先保存当前值
        original_request_id = get_request_id()
        
        with with_request_context("test-request", "test-session"):
            assert get_request_id() == "test-request"
            assert get_session_id() == "test-session"
        
        # 退出上下文后应该恢复到进入前的值
        assert get_request_id() == original_request_id


class TestStructuredLogger:
    """结构化日志器测试"""
    
    def test_logger_methods(self):
        """测试日志器方法"""
        logger = StructuredLogger("test")
        
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")
    
    def test_log_with_context(self):
        """测试带上下文的日志记录"""
        logger = StructuredLogger("test")
        set_request_id("test-request-123")
        logger.log_with_context("INFO", "test message", extra_field="value")


class TestJsonFormatter:
    """JSON 格式器测试"""
    
    def test_json_formatter(self):
        """测试 JSON 格式器"""
        record = {
            "time": __import__("datetime").datetime.now(),
            "level": __import__("loguru").logger.level("INFO"),
            "name": "test_module",
            "function": "test_func",
            "line": 42,
            "message": "test message"
        }
        result = json_formatter(record)
        assert isinstance(result, str)
        
        import json
        parsed = json.loads(result)
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "module" in parsed
        assert "message" in parsed
