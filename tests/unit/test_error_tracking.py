"""错误追踪模块单元测试"""
import pytest
from backend.utils.error_tracking import (
    ErrorTracker,
    error_tracker,
    capture_exception,
    capture_message,
    error_handler_middleware,
    get_error_info
)


class TestErrorTracker:
    """错误追踪器测试"""

    def test_error_tracker_creation(self):
        tracker = ErrorTracker()
        assert tracker is not None
        assert hasattr(tracker, '_error_counts')
        assert hasattr(tracker, '_last_error_time')

    def test_track_error(self):
        tracker = ErrorTracker()
        result = tracker.track_error("test_error", "test_message")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_track_error_with_exception(self):
        tracker = ErrorTracker()
        try:
            raise ValueError("test exception")
        except ValueError as e:
            result = tracker.track_error("ValueError", str(e))
            assert result is not None
            assert isinstance(result, str)

    def test_track_error_with_extra_info(self):
        tracker = ErrorTracker()
        result = tracker.track_error(
            "test_error",
            "test_message",
            request_id="req-123",
            endpoint="/test",
            method="POST"
        )
        assert result is not None

    def test_get_error_stats(self):
        tracker = ErrorTracker()
        tracker.track_error("TypeError", "msg1")
        tracker.track_error("TypeError", "msg2")
        tracker.track_error("ValueError", "msg3")

        stats = tracker.get_error_stats()
        assert "error_counts" in stats
        assert "total_errors" in stats
        assert "error_types" in stats
        assert stats["total_errors"] == 3
        assert stats["error_counts"].get("TypeError") == 2
        assert stats["error_counts"].get("ValueError") == 1

    def test_reset_stats(self):
        tracker = ErrorTracker()
        tracker.track_error("test", "message")
        tracker.reset_stats()
        stats = tracker.get_error_stats()
        assert stats["total_errors"] == 0
        assert len(stats["error_types"]) == 0


class TestGlobalErrorTracker:
    """全局错误追踪器测试"""

    def test_error_tracker_singleton(self):
        tracker1 = error_tracker
        assert tracker1 is not None
        assert isinstance(tracker1, ErrorTracker)


class TestCaptureFunctions:
    """捕获函数测试"""

    def test_capture_exception(self):
        try:
            raise ValueError("test exception")
        except ValueError as e:
            error_id = capture_exception(e)
            assert error_id is not None
            assert isinstance(error_id, str)

    def test_capture_message(self):
        error_id = capture_message("test message", "CustomError")
        assert error_id is not None
        assert isinstance(error_id, str)


class TestErrorHandlerMiddleware:
    """错误处理中间件测试"""

    def test_error_handler_middleware_sync(self):
        @error_handler_middleware
        def sync_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            sync_func()

    @pytest.mark.asyncio
    async def test_error_handler_middleware_async(self):
        @error_handler_middleware
        async def async_func():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            await async_func()


class TestGetErrorInfo:
    """获取错误信息测试"""

    def test_get_error_info(self):
        result = get_error_info("nonexistent")
        assert result is None
