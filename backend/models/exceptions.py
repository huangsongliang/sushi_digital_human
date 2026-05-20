"""
自定义异常定义
提供应用特定的异常类型，便于错误处理和日志记录
"""

from typing import Optional, Any, Dict


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"[{self.error_code}] {self.message} | Details: {self.details}"
        return f"[{self.error_code}] {self.message}"


class LLMException(AppException):
    """大语言模型调用异常"""

    def __init__(
        self,
        message: str,
        model: Optional[str] = None,
        retry_count: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.model = model
        self.retry_count = retry_count
        details = details or {}
        details.update({"model": model, "retry_count": retry_count})
        super().__init__(message, error_code="LLM_ERROR", details=details)


class LLMTimeoutException(LLMException):
    """LLM 调用超时异常"""

    def __init__(
        self,
        timeout: int,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.timeout = timeout
        details = details or {}
        details["timeout"] = timeout
        super().__init__(
            message=f"LLM 调用超时（{timeout}秒）", model=model, details=details
        )
        self.error_code = "LLM_TIMEOUT"


class LLMConnectionException(LLMException):
    """LLM 连接异常"""

    def __init__(
        self,
        reason: str,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["reason"] = reason
        super().__init__(
            message=f"LLM 连接失败: {reason}", model=model, details=details
        )
        self.error_code = "LLM_CONNECTION_ERROR"


class RetrievalException(AppException):
    """检索异常基类"""

    def __init__(
        self,
        message: str,
        method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.method = method
        details = details or {}
        details["method"] = method
        super().__init__(message, error_code="RETRIEVAL_ERROR", details=details)


class VectorStoreException(RetrievalException):
    """向量存储异常"""

    def __init__(
        self,
        message: str,
        collection: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.collection = collection
        details = details or {}
        details["collection"] = collection
        super().__init__(message, method="vector_store", details=details)
        self.error_code = "VECTOR_STORE_ERROR"


class EmptyRetrievalResultException(RetrievalException):
    """检索结果为空异常"""

    def __init__(self, query: str, details: Optional[Dict[str, Any]] = None):
        self.query = query
        details = details or {}
        details["query"] = query
        super().__init__(message="检索结果为空", method="hybrid", details=details)
        self.error_code = "EMPTY_RETRIEVAL"


class MemoryException(AppException):
    """记忆/会话存储异常"""

    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.session_id = session_id
        details = details or {}
        details["session_id"] = session_id
        super().__init__(message, error_code="MEMORY_ERROR", details=details)


class RedisConnectionException(MemoryException):
    """Redis 连接异常"""

    def __init__(
        self,
        reason: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["reason"] = reason
        super().__init__(
            message=f"Redis 连接失败: {reason}", session_id=session_id, details=details
        )
        self.error_code = "REDIS_CONNECTION_ERROR"


class ConfigurationException(AppException):
    """配置异常"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.config_key = config_key
        details = details or {}
        details["config_key"] = config_key
        super().__init__(message, error_code="CONFIG_ERROR", details=details)


class ValidationException(AppException):
    """数据验证异常"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.field = field
        self.value = value
        details = details or {}
        details.update({"field": field, "value": value})
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class RateLimitException(AppException):
    """限流异常"""

    def __init__(
        self,
        client_ip: str,
        limit: int,
        window: int = 60,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details.update({"client_ip": client_ip, "limit": limit, "window": window})
        super().__init__(
            message=f"请求过于频繁，请 {window} 秒后重试",
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class AuthenticationException(AppException):
    """认证异常"""

    def __init__(
        self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code="AUTH_ERROR", details=details)


class AuthorizationException(AppException):
    """授权异常"""

    def __init__(
        self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)
