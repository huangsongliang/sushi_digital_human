"""
细粒度权限管理模块（已弃用 - 内存版）

⚠️ DEPRECATED: 本模块为内存版权限管理器，仅用于开发和单机场景。
生产环境请使用 backend.core.auth_manager.PermissionManager（数据库版），
该版本持久化到 MySQL 并支持多进程共享，拥有完整的 RBAC 功能。

本模块提供：
- 基于角色的访问控制（RBAC）
- 文档级权限控制
- 自定义权限检查
- 权限验证装饰器
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from functools import wraps
from fastapi import Depends, HTTPException, status

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PermissionAction(Enum):
    """权限操作枚举"""

    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    DELETE = "delete"
    CREATE = "create"
    MANAGE = "manage"


class ResourceType(Enum):
    """资源类型枚举"""

    DOCUMENT = "document"
    CONVERSATION = "conversation"
    USER = "user"
    ROLE = "role"
    SYSTEM = "system"


@dataclass
class Permission:
    """权限定义"""

    name: str
    resource_type: ResourceType
    action: PermissionAction
    description: str = ""


@dataclass
class RolePermission:
    """角色权限关联"""

    role_name: str
    permissions: List[Permission]


class PermissionManager:
    """
    权限管理器（内存版，已弃用）

    ⚠️ 线程安全警告: 本管理器使用普通 dict 存储数据，
    多线程并发读写存在竞态条件。生产环境请使用数据库版。
    """

    def __init__(self):
        self._roles: Dict[str, List[Permission]] = {}
        self._user_roles: Dict[int, List[str]] = {}
        self._document_permissions: Dict[int, Dict[int, List[str]]] = {}  # doc_id -> user_id -> permissions
        self._default_permissions = {
            "admin": [
                Permission("document_read", ResourceType.DOCUMENT, PermissionAction.READ),
                Permission("document_write", ResourceType.DOCUMENT, PermissionAction.WRITE),
                Permission("document_edit", ResourceType.DOCUMENT, PermissionAction.EDIT),
                Permission("document_delete", ResourceType.DOCUMENT, PermissionAction.DELETE),
                Permission("document_create", ResourceType.DOCUMENT, PermissionAction.CREATE),
                Permission("user_manage", ResourceType.USER, PermissionAction.MANAGE),
                Permission("role_manage", ResourceType.ROLE, PermissionAction.MANAGE),
                Permission("system_manage", ResourceType.SYSTEM, PermissionAction.MANAGE),
            ],
            "editor": [
                Permission("document_read", ResourceType.DOCUMENT, PermissionAction.READ),
                Permission("document_write", ResourceType.DOCUMENT, PermissionAction.WRITE),
                Permission("document_edit", ResourceType.DOCUMENT, PermissionAction.EDIT),
                Permission("document_create", ResourceType.DOCUMENT, PermissionAction.CREATE),
            ],
            "viewer": [
                Permission("document_read", ResourceType.DOCUMENT, PermissionAction.READ),
            ],
        }

    def add_role(self, role_name: str, permissions: List[Permission]):
        """添加角色"""
        self._roles[role_name] = permissions
        logger.info(f"已添加角色: {role_name}")

    def remove_role(self, role_name: str):
        """删除角色"""
        if role_name in self._roles:
            del self._roles[role_name]
            logger.info(f"已删除角色: {role_name}")

    def get_role_permissions(self, role_name: str) -> List[Permission]:
        """获取角色权限"""
        return self._roles.get(role_name, [])

    def assign_role_to_user(self, user_id: int, role_name: str):
        """为用户分配角色"""
        if user_id not in self._user_roles:
            self._user_roles[user_id] = []
        if role_name not in self._user_roles[user_id]:
            self._user_roles[user_id].append(role_name)
            logger.info(f"用户 {user_id} 已分配角色: {role_name}")

    def remove_role_from_user(self, user_id: int, role_name: str):
        """从用户移除角色"""
        if user_id in self._user_roles and role_name in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role_name)
            logger.info(f"用户 {user_id} 已移除角色: {role_name}")

    def get_user_roles(self, user_id: int) -> List[str]:
        """获取用户角色"""
        return self._user_roles.get(user_id, [])

    def set_document_permission(self, doc_id: int, user_id: int, permissions: List[str]):
        """设置文档级权限"""
        if doc_id not in self._document_permissions:
            self._document_permissions[doc_id] = {}
        self._document_permissions[doc_id][user_id] = permissions
        logger.info(f"文档 {doc_id} 已设置用户 {user_id} 权限: {permissions}")

    def get_document_permissions(self, doc_id: int, user_id: int) -> List[str]:
        """获取用户在文档上的权限"""
        return self._document_permissions.get(doc_id, {}).get(user_id, [])

    def has_permission(
        self, user_id: int, resource_type: ResourceType, action: PermissionAction, resource_id: Optional[int] = None
    ) -> bool:
        """检查用户是否有指定权限"""
        # 超级管理员拥有所有权限
        if "admin" in self.get_user_roles(user_id):
            return True

        # 检查角色权限
        roles = self.get_user_roles(user_id)
        for role in roles:
            permissions = self.get_role_permissions(role)
            for perm in permissions:
                if perm.resource_type == resource_type and perm.action == action:
                    return True

        # 检查文档级权限（如果有资源ID）
        if resource_id is not None and resource_type == ResourceType.DOCUMENT:
            doc_perms = self.get_document_permissions(resource_id, user_id)
            if action.value in doc_perms:
                return True

        return False

    def can_read(self, user_id: int, resource_type: ResourceType, resource_id: Optional[int] = None) -> bool:
        """检查是否有读取权限"""
        return self.has_permission(user_id, resource_type, PermissionAction.READ, resource_id)

    def can_write(self, user_id: int, resource_type: ResourceType, resource_id: Optional[int] = None) -> bool:
        """检查是否有写入权限"""
        return self.has_permission(user_id, resource_type, PermissionAction.WRITE, resource_id)

    def can_edit(self, user_id: int, resource_type: ResourceType, resource_id: Optional[int] = None) -> bool:
        """检查是否有编辑权限"""
        return self.has_permission(user_id, resource_type, PermissionAction.EDIT, resource_id)

    def can_delete(self, user_id: int, resource_type: ResourceType, resource_id: Optional[int] = None) -> bool:
        """检查是否有删除权限"""
        return self.has_permission(user_id, resource_type, PermissionAction.DELETE, resource_id)

    def can_create(self, user_id: int, resource_type: ResourceType) -> bool:
        """检查是否有创建权限"""
        return self.has_permission(user_id, resource_type, PermissionAction.CREATE)

    def initialize_default_roles(self):
        """初始化默认角色"""
        for role_name, permissions in self._default_permissions.items():
            self.add_role(role_name, permissions)
        logger.info("默认角色已初始化")


# 全局权限管理器实例
permission_manager = PermissionManager()


def requires_permission(resource_type: ResourceType, action: PermissionAction):
    """权限验证装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 中获取 user_id
            user_id = kwargs.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供用户ID")

            # 检查权限
            if not permission_manager.has_permission(user_id, resource_type, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"用户 {user_id} 没有 {action.value} {resource_type.value} 的权限",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def requires_document_permission(action: PermissionAction):
    """文档权限验证装饰器"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            doc_id = kwargs.get("doc_id")

            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供用户ID")

            if not permission_manager.has_permission(user_id, ResourceType.DOCUMENT, action, doc_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"用户 {user_id} 没有 {action.value} 文档 {doc_id} 的权限",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def initialize_permission_system():
    """初始化权限系统"""
    permission_manager.initialize_default_roles()


def get_permission_manager() -> PermissionManager:
    """获取权限管理器（用于依赖注入）"""
    return permission_manager
