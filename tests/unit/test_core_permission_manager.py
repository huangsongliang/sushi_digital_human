"""核心权限管理模块单元测试"""

from backend.core.permission_manager import (
    Permission,
    PermissionAction,
    PermissionManager,
    ResourceType,
)


class TestPermissionAction:
    """PermissionAction 枚举测试"""

    def test_enum_values(self):
        assert PermissionAction.READ.value == "read"
        assert PermissionAction.WRITE.value == "write"
        assert PermissionAction.DELETE.value == "delete"
        assert PermissionAction.MANAGE.value == "manage"
        assert PermissionAction.EDIT.value == "edit"
        assert PermissionAction.CREATE.value == "create"


class TestResourceType:
    """ResourceType 枚举测试"""

    def test_enum_values(self):
        assert ResourceType.DOCUMENT.value == "document"
        assert ResourceType.CONVERSATION.value == "conversation"
        assert ResourceType.USER.value == "user"
        assert ResourceType.SYSTEM.value == "system"
        assert ResourceType.ROLE.value == "role"


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
        assert isinstance(mgr._roles, dict)
        assert isinstance(mgr._user_roles, dict)

    def test_add_role(self):
        mgr = PermissionManager()
        perm = Permission("read", ResourceType.DOCUMENT, PermissionAction.READ)
        mgr.add_role("tester", [perm])
        assert "tester" in mgr._roles

    def test_get_role_permissions(self):
        mgr = PermissionManager()
        perms = mgr.get_role_permissions("nonexistent")
        assert perms == []

    def test_assign_role_to_user(self):
        mgr = PermissionManager()
        mgr.assign_role_to_user(1, "admin")
        roles = mgr.get_user_roles(1)
        assert "admin" in roles

    def test_remove_role_from_user(self):
        mgr = PermissionManager()
        mgr.assign_role_to_user(1, "viewer")
        mgr.remove_role_from_user(1, "viewer")
        roles = mgr.get_user_roles(1)
        assert "viewer" not in roles

    def test_set_document_permission(self):
        mgr = PermissionManager()
        mgr.set_document_permission(100, 1, ["read"])
        assert 100 in mgr._document_permissions

    def test_default_permissions_exist(self):
        mgr = PermissionManager()
        assert "admin" in mgr._default_permissions
        assert "editor" in mgr._default_permissions
        assert "viewer" in mgr._default_permissions
