"""日志模块单元测试"""
from backend.utils.logger import (
    set_request_id,
    get_request_id,
    set_session_id,
    get_session_id,
    logger
)


class TestRequestTracking:
    """请求追踪测试"""

    def test_set_get_request_id(self):
        set_request_id("req-123")
        assert get_request_id() == "req-123"

    def test_set_get_session_id(self):
        set_session_id("session-123")
        assert get_session_id() == "session-123"


class TestStructuredLogger:
    """结构化日志测试"""

    def test_logger_methods(self):
        assert logger is not None
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_log_with_context(self):
        logger.info("test message", extra={"key": "value"})
