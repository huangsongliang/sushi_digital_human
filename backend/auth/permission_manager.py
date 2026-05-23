"""权限管理模块
实现基于 RBAC + ABAC 的细粒度权限控制
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PermissionAction(str, Enum):
    """权限操作"""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"


class PermissionResource(str, Enum):
    """权限资源类型"""

    DOCUMENT = "document"
    FOLDER = "folder"
    KNOWLEDGE_BASE = "knowledge_base"
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    SYSTEM = "system"


class PermissionManager:
    """权限管理器"""

    def __init__(self):
        self.cache = {}

    def check_permission(
        self,
        user_id: str,
        resource_type: PermissionResource,
        resource_id: str,
        action: PermissionAction,
    ) -> bool:
        """检查用户是否有权限"""
        cache_key = f"{user_id}:{resource_type}:{resource_id}:{action}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        user_roles = self._get_user_roles(user_id)
        if not user_roles:
            return False

        for role in user_roles:
            if self._role_has_permission(role, resource_type, action):
                self.cache[cache_key] = True
                return True

        if self._check_resource_acl(user_id, resource_type, resource_id, action):
            self.cache[cache_key] = True
            return True

        self.cache[cache_key] = False
        return False

    def _get_user_roles(self, user_id: str) -> List[str]:
        """获取用户角色"""
        try:
            result = db.execute(
                """
                SELECT role_id FROM user_roles
                WHERE user_id = %s
                """,
                (user_id,),
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"获取用户角色失败: {str(e)}")
            return []

    def _role_has_permission(
        self, role_id: str, resource_type: PermissionResource, action: PermissionAction
    ) -> bool:
        """检查角色是否有权限"""
        try:
            result = db.execute(
                """
                SELECT 1 FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                WHERE rp.role_id = %s
                AND p.resource_type = %s
                AND p.action = %s
                """,
                (role_id, resource_type.value, action.value),
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"检查角色权限失败: {str(e)}")
            return False

    def _check_resource_acl(
        self, user_id: str, resource_type: PermissionResource, resource_id: str, action: PermissionAction
    ) -> bool:
        """检查资源 ACL"""
        try:
            result = db.execute(
                """
                SELECT 1 FROM resource_acl
                WHERE resource_type = %s
                AND resource_id = %s
                AND user_id = %s
                AND action = %s
                """,
                (resource_type.value, resource_id, user_id, action.value),
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"检查资源 ACL 失败: {str(e)}")
            return False

    def grant_permission(
        self,
        user_id: str,
        resource_type: PermissionResource,
        resource_id: str,
        action: PermissionAction,
        granted_by: str,
    ) -> bool:
        """授予权限"""
        try:
            db.execute(
                """
                INSERT INTO resource_acl (id, user_id, resource_type, resource_id, action, granted_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE granted_by = %s, created_at = %s
                """,
                (
                    str(uuid4()),
                    user_id,
                    resource_type.value,
                    resource_id,
                    action.value,
                    granted_by,
                    datetime.now(),
                    granted_by,
                    datetime.now(),
                ),
            )
            db.commit()

            self._clear_cache(user_id)
            logger.info(f"权限授予成功: user={user_id}, resource={resource_type}:{resource_id}, action={action}")
            return True

        except Exception as e:
            logger.error(f"授予权限失败: {str(e)}")
            db.rollback()
            return False

    def revoke_permission(
        self,
        user_id: str,
        resource_type: PermissionResource,
        resource_id: str,
        action: PermissionAction,
    ) -> bool:
        """撤销权限"""
        try:
            db.execute(
                """
                DELETE FROM resource_acl
                WHERE user_id = %s
                AND resource_type = %s
                AND resource_id = %s
                AND action = %s
                """,
                (user_id, resource_type.value, resource_id, action.value),
            )
            db.commit()

            self._clear_cache(user_id)
            logger.info(f"权限撤销成功: user={user_id}, resource={resource_type}:{resource_id}")
            return True

        except Exception as e:
            logger.error(f"撤销权限失败: {str(e)}")
            db.rollback()
            return False

    def _clear_cache(self, user_id: str):
        """清除缓存"""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.cache[key]

    def get_user_permissions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有权限"""
        try:
            result = db.execute(
                """
                SELECT DISTINCT p.resource_type, p.action
                FROM user_roles ur
                JOIN role_permissions rp ON ur.role_id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE ur.user_id = %s

                UNION

                SELECT racl.resource_type, racl.action
                FROM resource_acl racl
                WHERE racl.user_id = %s
                """,
                (user_id, user_id),
            )

            permissions = []
            for row in result.fetchall():
                permissions.append(
                    {
                        "resource_type": row[0],
                        "action": row[1],
                    }
                )

            return permissions

        except Exception as e:
            logger.error(f"获取用户权限失败: {str(e)}")
            return []

    def get_resource_acl(self, resource_type: PermissionResource, resource_id: str) -> List[Dict[str, Any]]:
        """获取资源 ACL"""
        try:
            result = db.execute(
                """
                SELECT racl.user_id, racl.action, racl.granted_by, racl.created_at
                FROM resource_acl racl
                WHERE racl.resource_type = %s
                AND racl.resource_id = %s
                """,
                (resource_type.value, resource_id),
            )

            acl = []
            for row in result.fetchall():
                acl.append(
                    {
                        "user_id": row[0],
                        "action": row[1],
                        "granted_by": row[2],
                        "created_at": str(row[3]),
                    }
                )

            return acl

        except Exception as e:
            logger.error(f"获取资源 ACL 失败: {str(e)}")
            return []

    def create_role(self, role_name: str, description: str, permissions: List[Dict[str, str]]) -> Optional[str]:
        """创建角色"""
        try:
            role_id = str(uuid4())

            db.execute(
                """
                INSERT INTO roles (id, name, description, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (role_id, role_name, description, datetime.now()),
            )

            for perm in permissions:
                perm_id = self._get_or_create_permission(
                    perm["resource_type"], perm["action"]
                )

                if perm_id:
                    db.execute(
                        """
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        """,
                        (role_id, perm_id),
                    )

            db.commit()
            logger.info(f"角色创建成功: {role_name} (id={role_id})")
            return role_id

        except Exception as e:
            logger.error(f"创建角色失败: {str(e)}")
            db.rollback()
            return None

    def _get_or_create_permission(
        self, resource_type: str, action: str
    ) -> Optional[str]:
        """获取或创建权限"""
        try:
            result = db.execute(
                """
                SELECT id FROM permissions
                WHERE resource_type = %s AND action = %s
                """,
                (resource_type, action),
            )
            row = result.fetchone()

            if row:
                return row[0]

            perm_id = str(uuid4())
            db.execute(
                """
                INSERT INTO permissions (id, resource_type, action, description)
                VALUES (%s, %s, %s, %s)
                """,
                (perm_id, resource_type, action, f"{action} {resource_type}"),
            )
            db.commit()

            return perm_id

        except Exception as e:
            logger.error(f"获取或创建权限失败: {str(e)}")
            return None

    def assign_role_to_user(self, user_id: str, role_id: str, assigned_by: str) -> bool:
        """为用户分配角色"""
        try:
            db.execute(
                """
                INSERT INTO user_roles (user_id, role_id, assigned_by, created_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE assigned_by = %s, created_at = %s
                """,
                (user_id, role_id, assigned_by, datetime.now(), assigned_by, datetime.now()),
            )
            db.commit()

            self._clear_cache(user_id)
            logger.info(f"角色分配成功: user={user_id}, role={role_id}")
            return True

        except Exception as e:
            logger.error(f"分配角色失败: {str(e)}")
            db.rollback()
            return False

    def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """移除用户角色"""
        try:
            db.execute(
                """
                DELETE FROM user_roles
                WHERE user_id = %s AND role_id = %s
                """,
                (user_id, role_id),
            )
            db.commit()

            self._clear_cache(user_id)
            logger.info(f"角色移除成功: user={user_id}, role={role_id}")
            return True

        except Exception as e:
            logger.error(f"移除角色失败: {str(e)}")
            db.rollback()
            return False

    def get_all_roles(self) -> List[Dict[str, Any]]:
        """获取所有角色"""
        try:
            result = db.execute("SELECT id, name, description, created_at FROM roles")
            roles = []
            for row in result.fetchall():
                roles.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "created_at": str(row[3]),
                    }
                )
            return roles

        except Exception as e:
            logger.error(f"获取角色列表失败: {str(e)}")
            return []

    def get_role_permissions(self, role_id: str) -> List[Dict[str, Any]]:
        """获取角色权限"""
        try:
            result = db.execute(
                """
                SELECT p.id, p.resource_type, p.action, p.description
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = %s
                """,
                (role_id,),
            )

            permissions = []
            for row in result.fetchall():
                permissions.append(
                    {
                        "id": row[0],
                        "resource_type": row[1],
                        "action": row[2],
                        "description": row[3],
                    }
                )

            return permissions

        except Exception as e:
            logger.error(f"获取角色权限失败: {str(e)}")
            return []


_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """获取权限管理器实例"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
        logger.info("权限管理器已初始化")
    return _permission_manager
