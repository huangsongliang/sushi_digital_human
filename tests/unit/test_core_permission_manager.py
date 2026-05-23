"""核心权限管理模块单元测试"""

import pytest
from backend.core.permission_manager import (
    PermissionAction,
    ResourceType,
    Permission,
    PermissionManager,
)


class TestPermissionAction:
    """PermissionAction 枚举测试"""

    def test_enum_values(self):
        assert PermissionAction.READ.value == "read"
        assert PermissionAction.WRITE.value == "write"
        assert PermissionAction.DELETE.value == "delete"
        assert PermissionAction.MANAGE.value == "manage"


class TestResourceType:
    """ResourceType 枚举测试"""

    def test_enum_values(self):
        assert ResourceType.DOCUMENT.value == "document"
        assert ResourceType.CONVERSATION.value == "conversation"
        assert ResourceType.USER.value == "user"
        assert ResourceType.SYSTEM.value == "system"


class TestPermission:
    """Permission 数据类测试"""

    def test_creation(self):
        perm = Permission(
            name="read_docs",
            resource_type=ResourceType.DOCUMENT,
            action=PermissionAction.READ,
            description="阅读文档权限",
        )
        assert perm.name == "read_docs"
        assert perm.resource_type == ResourceType.DOCUMENT
        assert perm.action == PermissionAction.READ


class TestPermissionManager:
    """PermissionManager 测试"""

    def test_manager_creation(self):
        mgr = PermissionManager()
        assert mgr is not None
        assert isinstance(mgr._roles, dict)

    def test_admin_role_exists(self):
        mgr = PermissionManager()
        assert "admin" in mgr._roles

    def test_editor_role_exists(self):
        mgr = PermissionManager()
        assert "editor" in mgr._roles

    def test_viewer_role_exists(self):
        mgr = PermissionManager()
        assert "viewer" in mgr._roles

    def test_check_permission_admin(self):
        """管理员应拥有所有权限"""
        mgr = PermissionManager()
        mgr._user_roles["u1"] = ["admin"]
        result = mgr.check_permission(
            user_id="u1",
            resource_type="document",
            resource_id="d1",
            action=PermissionAction.READ,
        )
        assert result is True

    def test_check_permission_no_user(self):
        """不存在的用户应返回 False"""
        mgr = PermissionManager()
        result = mgr.check_permission(
            user_id="nonexistent",
            resource_type="document",
            resource_id="d1",
            action=PermissionAction.READ,
        )
        assert result is False
