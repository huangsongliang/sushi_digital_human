"""
API 市场模块
提供标准化 API 接口管理功能，支持：
- API 端点注册和发现
- API 文档生成
- API 版本管理
- API 访问统计
- API 密钥管理
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class APICategory(Enum):
    """API 分类枚举"""

    CHAT = "chat"  # 对话接口
    DOCUMENT = "document"  # 文档接口
    RETRIEVAL = "retrieval"  # 检索接口
    SUMMARY = "summary"  # 总结接口
    INTEGRATION = "integration"  # 集成接口
    SYSTEM = "system"  # 系统接口
    OTHER = "other"  # 其他


class APIStatus(Enum):
    """API 状态枚举"""

    ACTIVE = "active"  # 活跃
    DEPRECATED = "deprecated"  # 已弃用
    TESTING = "testing"  # 测试中
    INTERNAL = "internal"  # 内部使用


@dataclass
class APIEndpoint:
    """API 端点定义"""

    id: str
    name: str
    path: str
    method: str
    category: APICategory
    status: APIStatus
    description: str = ""
    version: str = "1.0"
    parameters: List[Dict[str, Any]] = None
    response_schema: Dict[str, Any] = None
    rate_limit: Optional[int] = None  # 每分钟调用限制
    requires_auth: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if self.parameters is None:
            self.parameters = []
        if self.response_schema is None:
            self.response_schema = {}
        if self.metadata is None:
            self.metadata = {}


@dataclass
class APIKey:
    """API 密钥"""

    key: str
    name: str
    user_id: Optional[int] = None
    created_at: datetime = None
    expires_at: Optional[datetime] = None
    revoked: bool = False
    rate_limit: Optional[int] = None
    allowed_endpoints: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if not self.key:
            self.key = self._generate_key()
        if not self.created_at:
            self.created_at = datetime.now()
        if self.allowed_endpoints is None:
            self.allowed_endpoints = []
        if self.metadata is None:
            self.metadata = {}

    def _generate_key(self) -> str:
        """生成 API 密钥"""
        return f"sk_{uuid.uuid4().hex[:32]}"

    def is_valid(self) -> bool:
        """检查密钥是否有效"""
        if self.revoked:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


@dataclass
class APIUsage:
    """API 使用统计"""

    endpoint_id: str
    api_key: str
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    last_access: Optional[datetime] = None

    def record_request(self, success: bool, latency: float):
        """记录请求"""
        self.request_count += 1
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
        self.total_latency += latency
        self.last_access = datetime.now()

    @property
    def avg_latency(self) -> float:
        """平均延迟"""
        if self.request_count > 0:
            return self.total_latency / self.request_count
        return 0.0

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.request_count > 0:
            return self.success_count / self.request_count
        return 0.0


class APIMarket:
    """API 市场管理器"""

    def __init__(self):
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._api_keys: Dict[str, APIKey] = {}
        self._usage: Dict[str, APIUsage] = {}  # endpoint_id -> APIUsage
        self._key_usage: Dict[str, APIUsage] = {}  # api_key -> APIUsage

    def register_endpoint(self, endpoint: APIEndpoint):
        """注册 API 端点"""
        self._endpoints[endpoint.id] = endpoint
        self._usage[endpoint.id] = APIUsage(endpoint_id=endpoint.id, api_key="")
        logger.info(f"已注册 API 端点: {endpoint.path}")

    def unregister_endpoint(self, endpoint_id: str):
        """注销 API 端点"""
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            if endpoint_id in self._usage:
                del self._usage[endpoint_id]
            logger.info(f"已注销 API 端点: {endpoint_id}")

    def get_endpoint(self, endpoint_id: str) -> Optional[APIEndpoint]:
        """获取端点信息"""
        return self._endpoints.get(endpoint_id)

    def get_endpoints_by_category(self, category: APICategory) -> List[APIEndpoint]:
        """按分类获取端点"""
        return [e for e in self._endpoints.values() if e.category == category]

    def get_all_endpoints(self) -> List[APIEndpoint]:
        """获取所有端点"""
        return list(self._endpoints.values())

    def create_api_key(
        self,
        name: str,
        user_id: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        rate_limit: Optional[int] = None,
        allowed_endpoints: Optional[List[str]] = None,
    ) -> APIKey:
        """创建 API 密钥"""
        api_key = APIKey(
            key="",
            name=name,
            user_id=user_id,
            expires_at=expires_at,
            rate_limit=rate_limit,
            allowed_endpoints=allowed_endpoints,
        )
        self._api_keys[api_key.key] = api_key
        self._key_usage[api_key.key] = APIUsage(endpoint_id="", api_key=api_key.key)
        logger.info(f"已创建 API 密钥: {name}")
        return api_key

    def get_api_key(self, key: str) -> Optional[APIKey]:
        """获取 API 密钥"""
        return self._api_keys.get(key)

    def validate_api_key(self, key: str) -> bool:
        """验证 API 密钥"""
        api_key = self._api_keys.get(key)
        if not api_key:
            return False
        return api_key.is_valid()

    def check_rate_limit(self, key: str, endpoint_id: str) -> bool:
        """检查速率限制"""
        api_key = self._api_keys.get(key)
        if not api_key:
            return False

        # 检查密钥级别的速率限制
        if api_key.rate_limit:
            usage = self._key_usage.get(key)
            if usage and usage.request_count >= api_key.rate_limit:
                return False

        # 检查端点级别的速率限制
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint and endpoint.rate_limit:
            usage = self._usage.get(endpoint_id)
            if usage and usage.request_count >= endpoint.rate_limit:
                return False

        return True

    def record_usage(self, api_key: str, endpoint_id: str, success: bool, latency: float):
        """记录 API 使用情况"""
        # 更新端点使用统计
        if endpoint_id in self._usage:
            self._usage[endpoint_id].record_request(success, latency)

        # 更新密钥使用统计
        if api_key in self._key_usage:
            self._key_usage[api_key].record_request(success, latency)

    def revoke_api_key(self, key: str):
        """撤销 API 密钥"""
        api_key = self._api_keys.get(key)
        if api_key:
            api_key.revoked = True
            logger.info(f"已撤销 API 密钥: {api_key.name}")

    def get_endpoint_usage(self, endpoint_id: str) -> Optional[APIUsage]:
        """获取端点使用统计"""
        return self._usage.get(endpoint_id)

    def get_key_usage(self, key: str) -> Optional[APIUsage]:
        """获取密钥使用统计"""
        return self._key_usage.get(key)

    def generate_openapi_spec(self) -> Dict[str, Any]:
        """生成 OpenAPI 规范"""
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "企业级智能文档问答平台 API",
                "version": "1.0.0",
                "description": "提供文档问答、检索、总结等功能的 RESTful API",
            },
            "paths": {},
        }

        for endpoint in self._endpoints.values():
            if endpoint.status != APIStatus.ACTIVE:
                continue

            path = spec["paths"].setdefault(endpoint.path, {})
            path[endpoint.method.lower()] = {
                "summary": endpoint.name,
                "description": endpoint.description,
                "parameters": endpoint.parameters,
                "responses": {
                    "200": {
                        "description": "成功",
                        "content": {"application/json": {"schema": endpoint.response_schema}},
                    }
                },
            }

            if endpoint.requires_auth:
                path[endpoint.method.lower()]["security"] = [{"ApiKeyAuth": []}]

        spec["components"] = {
            "securitySchemes": {"ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}}
        }

        return spec

    def generate_api_documentation(self) -> str:
        """生成 API 文档（Markdown 格式）"""
        markdown = "# API 文档\n\n"

        # 按分类分组
        categories = {}
        for endpoint in self._endpoints.values():
            if endpoint.category not in categories:
                categories[endpoint.category] = []
            categories[endpoint.category].append(endpoint)

        for category, endpoints in categories.items():
            markdown += f"## {category.value.capitalize()}\n\n"

            for endpoint in endpoints:
                status_badge = {
                    APIStatus.ACTIVE: "🟢",
                    APIStatus.DEPRECATED: "🔴",
                    APIStatus.TESTING: "🟡",
                    APIStatus.INTERNAL: "⚫",
                }.get(endpoint.status, "⚪")

                markdown += f"### {status_badge} {endpoint.name}\n\n"
                markdown += f"**路径**: `{endpoint.method} {endpoint.path}`\n\n"
                markdown += f"**版本**: {endpoint.version}\n\n"
                if endpoint.description:
                    markdown += f"**描述**: {endpoint.description}\n\n"

                if endpoint.parameters:
                    markdown += "**参数**:\n\n"
                    for param in endpoint.parameters:
                        required = param.get("required", False)
                        required_mark = "*" if required else ""
                        markdown += f"- `{param['name']}`{required_mark}: {param.get('description', '')}\n"
                    markdown += "\n"

                markdown += "---\n\n"

        return markdown


# 全局 API 市场实例
api_market = APIMarket()


def get_api_market() -> APIMarket:
    """获取 API 市场"""
    return api_market


def register_endpoint(
    name: str,
    path: str,
    method: str,
    category: str,
    description: str = "",
    version: str = "1.0",
    parameters: Optional[List[Dict[str, Any]]] = None,
    response_schema: Optional[Dict[str, Any]] = None,
    rate_limit: Optional[int] = None,
    requires_auth: bool = False,
):
    """注册 API 端点（对外接口）"""
    try:
        category_enum = APICategory[category.upper()]
        status_enum = APIStatus.ACTIVE
    except KeyError:
        logger.error(f"未知的 API 分类: {category}")
        return

    endpoint = APIEndpoint(
        id="",
        name=name,
        path=path,
        method=method,
        category=category_enum,
        status=status_enum,
        description=description,
        version=version,
        parameters=parameters,
        response_schema=response_schema,
        rate_limit=rate_limit,
        requires_auth=requires_auth,
    )

    api_market.register_endpoint(endpoint)


def create_api_key(
    name: str,
    user_id: Optional[int] = None,
    expires_days: Optional[int] = None,
    rate_limit: Optional[int] = None,
    allowed_endpoints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """创建 API 密钥（对外接口）"""
    expires_at = None
    if expires_days:
        expires_at = datetime.now() + timedelta(days=expires_days)

    api_key = api_market.create_api_key(
        name=name, user_id=user_id, expires_at=expires_at, rate_limit=rate_limit, allowed_endpoints=allowed_endpoints
    )

    return {
        "key": api_key.key,
        "name": api_key.name,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "rate_limit": api_key.rate_limit,
    }


def validate_api_key(key: str) -> bool:
    """验证 API 密钥（对外接口）"""
    return api_market.validate_api_key(key)


def record_api_usage(api_key: str, endpoint_id: str, success: bool, latency: float):
    """记录 API 使用（对外接口）"""
    api_market.record_usage(api_key, endpoint_id, success, latency)


def get_openapi_spec() -> Dict[str, Any]:
    """获取 OpenAPI 规范（对外接口）"""
    return api_market.generate_openapi_spec()


def get_api_documentation() -> str:
    """获取 API 文档（对外接口）"""
    return api_market.generate_api_documentation()
