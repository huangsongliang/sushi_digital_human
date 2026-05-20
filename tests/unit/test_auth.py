"""认证与权限管理单元测试"""

import pytest
from backend.core.auth_manager import AuthManager, PermissionManager
from backend.core.security import get_password_hash, verify_password
from backend.database.session import db_manager


async def setup_db():
    """设置数据库"""
    db_manager.init()
    await db_manager.create_tables()


async def teardown_db():
    """清理数据库"""
    await db_manager.drop_tables()
    await db_manager.dispose()


class TestPasswordHashing:
    """密码哈希测试"""

    def test_password_hash_verify(self):
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False


class TestAuthManager:
    """认证管理器测试"""

    @pytest.mark.asyncio
    async def test_register_user(self):
        await setup_db()
        try:
            auth_manager = AuthManager()

            result = await auth_manager.register_user(
                username="testuser",
                email="test@example.com",
                password="password123",
            )

            assert result.get("success") is True
        finally:
            await teardown_db()

    @pytest.mark.asyncio
    async def test_register_existing_user(self):
        await setup_db()
        try:
            auth_manager = AuthManager()

            await auth_manager.register_user(
                username="testuser2",
                email="test2@example.com",
                password="password123",
            )

            result = await auth_manager.register_user(
                username="testuser2",
                email="test2@example.com",
                password="password123",
            )

            assert result.get("success") is False
            assert "已存在" in result.get("error", "")
        finally:
            await teardown_db()


class TestPermissionManager:
    """权限管理器测试"""

    @pytest.mark.asyncio
    async def test_create_role(self):
        await setup_db()
        try:
            permission_manager = PermissionManager()

            success = await permission_manager.create_role(
                "test_role", "Test role description"
            )

            assert success is True
        finally:
            await teardown_db()

    @pytest.mark.asyncio
    async def test_create_permission(self):
        await setup_db()
        try:
            permission_manager = PermissionManager()

            success = await permission_manager.create_permission(
                "test:access", "test", "access", "Test permission"
            )

            assert success is True
        finally:
            await teardown_db()

    @pytest.mark.asyncio
    async def test_assign_permission_to_role(self):
        await setup_db()
        try:
            permission_manager = PermissionManager()

            await permission_manager.create_role("test_role2", "Test role 2")
            await permission_manager.create_permission(
                "test:manage", "test", "manage", "Test manage permission"
            )

            success = await permission_manager.assign_permission_to_role(
                "test_role2", "test:manage"
            )

            assert success is True
        finally:
            await teardown_db()
