"""API 版本管理模块

提供 API 版本管理功能，支持：
- 版本路由前缀
- 版本兼容性处理
- 版本迁移指导
- 废弃警告

版本历史：
- v1: 初始版本
- v2: 新增多模态能力、工作流引擎
- v3: 新增 Agent 框架、知识图谱
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# 当前版本
CURRENT_VERSION = "v1"
SUPPORTED_VERSIONS = ["v1"]

# 版本映射
VERSION_ROUTES = {
    "v1": {
        "prefix": "/api/v1",
        "description": "初始版本",
        "endpoints": [
            "/chat",
            "/documents",
            "/auth",
            "/agents",
            "/workflow",
            "/multimodal",
            "/knowledge_graph",
            "/audit",
            "/permissions",
            "/tracing",
            "/alerts",
            "/deployment",
            "/ab_test",
            "/cicd",
        ],
    }
}


class VersionInfo(BaseModel):
    """版本信息"""

    version: str
    is_current: bool
    is_deprecated: bool
    description: str
    release_date: Optional[str] = None
    endpoints: List[str] = []


class VersionListResponse(BaseModel):
    """版本列表响应"""

    current_version: str
    supported_versions: List[str]
    versions: List[VersionInfo]


class MigrationGuide(BaseModel):
    """迁移指南"""

    from_version: str
    to_version: str
    changes: List[Dict[str, Any]]
    affected_endpoints: List[str]
    migration_notes: str


# 版本信息配置
VERSION_INFO: Dict[str, VersionInfo] = {
    "v1": VersionInfo(
        version="v1",
        is_current=True,
        is_deprecated=False,
        description="初始版本 - 包含文档问答、多模态能力、工作流引擎、智能Agent等核心功能",
        release_date="2024-01-01",
        endpoints=VERSION_ROUTES["v1"]["endpoints"],
    ),
}


# ==================== 版本管理路由 ====================

router = APIRouter(prefix="/api/version", tags=["版本管理"])


@router.get("/", response_model=VersionListResponse)
async def get_version_info():
    """获取所有版本信息"""
    return {
        "current_version": CURRENT_VERSION,
        "supported_versions": SUPPORTED_VERSIONS,
        "versions": list(VERSION_INFO.values()),
    }


@router.get("/current")
async def get_current_version():
    """获取当前版本"""
    return {
        "version": CURRENT_VERSION,
        "app_version": settings.app_version,
        "description": VERSION_INFO[CURRENT_VERSION].description,
    }


@router.get("/{version}")
async def get_version_detail(version: str):
    """获取特定版本详情"""
    if version not in VERSION_INFO:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"版本 {version} 不存在",
        )

    version_info = VERSION_INFO[version]
    return {
        **version_info.dict(),
        "app_version": settings.app_version,
    }


@router.get("/{version}/endpoints")
async def get_version_endpoints(version: str):
    """获取版本支持的端点"""
    if version not in VERSION_INFO:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"版本 {version} 不存在",
        )

    return {
        "version": version,
        "endpoints": VERSION_INFO[version].endpoints,
    }


@router.get("/{version}/deprecated")
async def check_version_deprecated(version: str):
    """检查版本是否已废弃"""
    if version not in VERSION_INFO:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"版本 {version} 不存在",
        )

    version_info = VERSION_INFO[version]
    return {
        "version": version,
        "is_deprecated": version_info.is_deprecated,
        "message": "该版本已废弃，请升级到最新版本" if version_info.is_deprecated else "该版本当前有效",
    }


# ==================== 版本中间件 ====================


class VersionMiddleware:
    """API 版本管理中间件"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # 检查版本前缀
        version = self._extract_version(path)

        if version:
            # 验证版本
            if version not in SUPPORTED_VERSIONS:
                await self._send_version_error(send, version)
                return

            # 设置版本信息到 scope
            scope["version"] = version
            scope["state"]["api_version"] = version

            # 如果版本已废弃，添加警告头
            if VERSION_INFO.get(version, {}).get("is_deprecated", False):
                scope["state"]["version_warning"] = f"版本 {version} 已废弃"

        await self.app(scope, receive, send)

    def _extract_version(self, path: str) -> Optional[str]:
        """从路径中提取版本号"""
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "api" and parts[1].startswith("v"):
            return parts[1]
        return None

    async def _send_version_error(self, send, version: str):
        """发送版本错误响应"""
        import json

        response_body = json.dumps(
            {
                "detail": f"不支持的 API 版本: {version}",
                "supported_versions": SUPPORTED_VERSIONS,
                "current_version": CURRENT_VERSION,
            }
        ).encode("utf-8")

        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(response_body)).encode()),
        ]

        await send(
            {
                "type": "http.response.start",
                "status": 400,
                "headers": headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": response_body,
            }
        )


# ==================== 版本装饰器 ====================


def version(versions: List[str]):
    """版本控制装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = None

            # 查找 request 对象
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                api_version = getattr(request.state, "api_version", None)

                if api_version and api_version not in versions:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"端点不支持版本 {api_version}，支持的版本: {versions}",
                    )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def deprecated_in(version: str):
    """标记在指定版本中废弃"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            request = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request:
                api_version = getattr(request.state, "api_version", CURRENT_VERSION)

                if api_version >= version:
                    logger.warning(f"调用已废弃的端点: {request.url.path}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ==================== 版本检查依赖 ====================


async def require_version(min_version: str = None, max_version: str = None):
    """依赖注入：版本检查"""

    async def dependency(request: Request):
        api_version = getattr(request.state, "api_version", CURRENT_VERSION)

        if min_version and api_version < min_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"需要最低版本 {min_version}，当前版本 {api_version}",
            )

        if max_version and api_version > max_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"该端点最高支持版本 {max_version}，当前版本 {api_version}",
            )

        return api_version

    return dependency


# ==================== 辅助函数 ====================


def get_version_from_request(request: Request) -> str:
    """从请求中获取版本号"""
    return getattr(request.state, "api_version", CURRENT_VERSION)


def is_version_deprecated(version: str) -> bool:
    """检查版本是否已废弃"""
    return VERSION_INFO.get(version, {}).get("is_deprecated", False)


def get_version_description(version: str) -> Optional[str]:
    """获取版本描述"""
    return VERSION_INFO.get(version, {}).get("description")
