"""异常模型单元测试"""
from backend.models.exceptions import (
    AppException,
    LLMException,
    LLMTimeoutException,
    LLMConnectionException,
    RetrievalException,
    VectorStoreException,
    EmptyRetrievalResultException,
    MemoryException
)


class TestAppException:
    """基础异常测试"""

    def test_app_exception_creation(self):
        exc = AppException("test error")
        assert exc.message == "test error"
        assert exc.error_code == "APP_ERROR"

    def test_app_exception_with_code(self):
        exc = AppException("test error", error_code="CUSTOM_ERROR")
        assert exc.error_code == "CUSTOM_ERROR"

    def test_app_exception_str(self):
        exc = AppException("test error", error_code="TEST_ERROR")
        result = str(exc)
        assert "TEST_ERROR" in result
        assert "test error" in result


class TestLLMException:
    """LLM异常测试"""

    def test_llm_exception(self):
        exc = LLMException("model error", model="test-model")
        assert exc.message == "model error"
        assert exc.model == "test-model"
        assert exc.error_code == "LLM_ERROR"


class TestLLMTimeoutException:
    """LLM超时异常测试"""

    def test_timeout_exception(self):
        exc = LLMTimeoutException(timeout=30, model="test-model")
        assert exc.timeout == 30
        assert exc.error_code == "LLM_TIMEOUT"


class TestLLMConnectionException:
    """LLM连接异常测试"""

    def test_connection_exception(self):
        exc = LLMConnectionException(
            reason="network error",
            model="test-model"
        )
        assert exc.error_code == "LLM_CONNECTION_ERROR"


class TestRetrievalException:
    """检索异常测试"""

    def test_retrieval_exception(self):
        exc = RetrievalException("retrieval failed", method="bm25")
        assert exc.method == "bm25"
        assert exc.error_code == "RETRIEVAL_ERROR"


class TestVectorStoreException:
    """向量存储异常测试"""

    def test_vector_store_exception(self):
        exc = VectorStoreException(
            "store error",
            collection="test-collection"
        )
        assert exc.collection == "test-collection"
        assert exc.error_code == "VECTOR_STORE_ERROR"


class TestEmptyRetrievalResultException:
    """空检索结果异常测试"""

    def test_empty_result_exception(self):
        exc = EmptyRetrievalResultException(query="test query")
        assert exc.query == "test query"
        assert exc.error_code == "EMPTY_RETRIEVAL"


class TestMemoryException:
    """记忆存储异常测试"""

    def test_memory_exception(self):
        exc = MemoryException("memory error", session_id="session-123")
        assert exc.session_id == "session-123"
        assert exc.error_code == "MEMORY_ERROR"
