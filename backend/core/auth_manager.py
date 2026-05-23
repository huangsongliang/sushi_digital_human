"""认证与权限管理服务"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.security import create_access_token, get_password_hash, verify_password, verify_token
from backend.database.models import Permission, Role, RolePermission, User, UserRole
from backend.database.session import get_db_session
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AuthManager:
    """认证管理器"""

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """注册新用户"""
        async with get_db_session() as session:
            existing_user = await session.execute(
                select(User).where(or_(User.username == username, User.email == email))
            )
            existing_user = existing_user.scalar_one_or_none()

            if existing_user:
                return {"success": False, "error": "用户名或邮箱已存在"}

            hashed_password = get_password_hash(password)
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            await self._assign_default_role(session, user.id)

            logger.info(f"用户注册成功: {username}")
            return {"success": True, "user_id": user.id, "username": username}

    async def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """用户登录"""
        async with get_db_session() as session:
            user = await session.execute(select(User).where(User.email == email))
            user = user.scalar_one_or_none()

            if not user or not user.is_active:
                return {"success": False, "error": "用户不存在或已禁用"}

            if not verify_password(password, user.hashed_password):
                return {"success": False, "error": "密码错误"}

            access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

            refresh_token = self._create_refresh_token(user.id)

            logger.info(f"用户登录成功: {user.username}")
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            }

    def _create_refresh_token(self, user_id: int) -> str:
        """创建刷新令牌"""
        token_data = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
        }
        return create_access_token(data=token_data)

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """刷新访问令牌"""
        try:
            payload = verify_token(refresh_token)
            if payload.get("type") != "refresh":
                return {"success": False, "error": "无效的刷新令牌"}

            user_id = payload.get("sub")
            if not user_id:
                return {"success": False, "error": "令牌无效"}

            async with get_db_session() as session:
                user = await session.get(User, int(user_id))
                if not user or not user.is_active:
                    return {"success": False, "error": "用户不存在或已禁用"}

                access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

                return {
                    "success": True,
                    "access_token": access_token,
                    "token_type": "bearer",
                }
        except Exception as e:
            logger.error(f"刷新令牌失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        async with get_db_session() as session:
            return await session.get(User, user_id)

    async def _generate_unique_username(self, session: AsyncSession, phone: str) -> str:
        """根据手机号生成唯一用户名"""
        username = f"user_{phone[-4:]}"
        while True:
            existing = await session.execute(select(User).where(User.username == username))
            existing = existing.scalar_one_or_none()
            if not existing:
                break
            username = f"user_{phone[-4:]}_{int(datetime.now().timestamp()) % 1000}"
        return username

    async def get_user_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        async with get_db_session() as session:
            result = await session.execute(select(User).where(User.phone == phone))
            return result.scalar_one_or_none()

    async def login_with_phone(self, phone: str) -> Dict[str, Any]:
        """手机号登录（验证码已验证通过）- 如果用户不存在则自动注册"""
        async with get_db_session() as session:
            user = await session.execute(select(User).where(User.phone == phone))
            user = user.scalar_one_or_none()

            # 如果用户不存在，自动注册
            if not user:
                logger.info(f"用户不存在，自动注册手机号: {phone}")

                # 生成随机用户名（基于手机号）
                username = await self._generate_unique_username(session, phone)

                user = User(
                    username=username,
                    phone=phone,
                    hashed_password=None,  # 手机号登录用户可以没有密码
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

                await self._assign_default_role(session, user.id)
                logger.info(f"自动注册成功: {username}")
            elif not user.is_active:
                return {"success": False, "error": "用户已禁用"}

            access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

            refresh_token = self._create_refresh_token(user.id)

            logger.info(f"用户手机号登录成功: {user.username}")
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "phone": user.phone,
                },
            }

    async def register_with_phone(self, phone: str, password: Optional[str] = None) -> Dict[str, Any]:
        """手机号注册"""
        async with get_db_session() as session:
            existing_user = await session.execute(select(User).where(User.phone == phone))
            existing_user = existing_user.scalar_one_or_none()

            if existing_user:
                return {"success": False, "error": "该手机号已被注册"}

            # 生成随机用户名（基于手机号）
            username = await self._generate_unique_username(session, phone)

            hashed_password = get_password_hash(password) if password else None

            user = User(
                username=username,
                phone=phone,
                hashed_password=hashed_password,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            await self._assign_default_role(session, user.id)

            logger.info(f"用户手机号注册成功: {username}")
            return {"success": True, "user_id": user.id, "username": username}

    async def _assign_default_role(self, session: AsyncSession, user_id: int):
        """为新用户分配默认角色"""
        default_role = await session.execute(select(Role).where(Role.name == "user"))
        default_role = default_role.scalar_one_or_none()

        if default_role:
            user_role = UserRole(user_id=user_id, role_id=default_role.id)
            session.add(user_role)
            await session.flush()

    async def login_with_oauth(
        self, provider: str, provider_id: str, username: str, email: Optional[str] = None
    ) -> Dict[str, Any]:
        """OAuth 登录 - 如果用户不存在则自动注册"""
        async with get_db_session() as session:
            # 检查是否已有绑定该 OAuth 的用户
            user = await session.execute(
                select(User).where(and_(User.oauth_provider == provider, User.oauth_id == provider_id))
            )
            user = user.scalar_one_or_none()

            # 如果用户不存在，检查是否有相同邮箱的用户
            if not user and email:
                user = await session.execute(select(User).where(User.email == email))
                user = user.scalar_one_or_none()

            # 如果用户不存在，自动注册
            if not user:
                logger.info(f"OAuth 用户不存在，自动注册: {provider}:{username}")

                # 确保用户名唯一
                base_username = username
                counter = 1
                while True:
                    existing = await session.execute(select(User).where(User.username == username))
                    existing = existing.scalar_one_or_none()
                    if not existing:
                        break
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = User(
                    username=username,
                    email=email,
                    oauth_provider=provider,
                    oauth_id=provider_id,
                    hashed_password=None,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)

                await self._assign_default_role(session, user.id)
                logger.info(f"OAuth 自动注册成功: {username}")
            elif not user.is_active:
                return {"success": False, "error": "用户已禁用"}
            elif not user.oauth_provider:
                # 如果用户存在但没有绑定 OAuth，进行绑定
                user.oauth_provider = provider
                user.oauth_id = provider_id
                await session.commit()
                logger.info(f"用户绑定 OAuth: {user.username} -> {provider}")

            access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

            refresh_token = self._create_refresh_token(user.id)

            logger.info(f"OAuth 登录成功: {user.username} ({provider})")
            return {
                "success": True,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            }


class PermissionManager:
    """权限管理器"""

    async def get_user_permissions(self, user_id: int) -> List[str]:
        """获取用户的所有权限"""
        async with get_db_session() as session:
            stmt = (
                select(Permission.name)
                .join(RolePermission)
                .join(Role)
                .join(UserRole)
                .where(UserRole.user_id == user_id)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def has_permission(self, user_id: int, permission_name: str) -> bool:
        """检查用户是否具有指定权限"""
        permissions = await self.get_user_permissions(user_id)
        return permission_name in permissions

    async def has_role(self, user_id: int, role_name: str) -> bool:
        """检查用户是否具有指定角色"""
        async with get_db_session() as session:
            stmt = select(Role).join(UserRole).where(and_(UserRole.user_id == user_id, Role.name == role_name))
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def get_user_roles(self, user_id: int) -> List[str]:
        """获取用户的所有角色"""
        async with get_db_session() as session:
            stmt = select(Role.name).join(UserRole).where(UserRole.user_id == user_id)
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]

    async def assign_role_to_user(self, user_id: int, role_name: str) -> bool:
        """为用户分配角色"""
        async with get_db_session() as session:
            role = await session.execute(select(Role).where(Role.name == role_name))
            role = role.scalar_one_or_none()

            if not role:
                return False

            existing = await session.execute(
                select(UserRole).where(and_(UserRole.user_id == user_id, UserRole.role_id == role.id))
            )
            existing = existing.scalar_one_or_none()

            if not existing:
                user_role = UserRole(user_id=user_id, role_id=role.id)
                session.add(user_role)
                await session.commit()

            return True

    async def create_role(self, name: str, description: str = "") -> bool:
        """创建角色"""
        async with get_db_session() as session:
            existing = await session.execute(select(Role).where(Role.name == name))
            existing = existing.scalar_one_or_none()

            if existing:
                return False

            role = Role(name=name, description=description, is_active=True)
            session.add(role)
            await session.commit()
            return True

    async def create_permission(self, name: str, resource: str, action: str, description: str = "") -> bool:
        """创建权限"""
        async with get_db_session() as session:
            existing = await session.execute(select(Permission).where(Permission.name == name))
            existing = existing.scalar_one_or_none()

            if existing:
                return False

            permission = Permission(
                name=name,
                description=description,
                resource=resource,
                action=action,
            )
            session.add(permission)
            await session.commit()
            return True

    async def assign_permission_to_role(self, role_name: str, permission_name: str) -> bool:
        """为角色分配权限"""
        async with get_db_session() as session:
            role = await session.execute(select(Role).where(Role.name == role_name))
            role = role.scalar_one_or_none()

            permission = await session.execute(select(Permission).where(Permission.name == permission_name))
            permission = permission.scalar_one_or_none()

            if not role or not permission:
                return False

            existing = await session.execute(
                select(RolePermission).where(
                    and_(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id,
                    )
                )
            )
            existing = existing.scalar_one_or_none()

            if not existing:
                role_permission = RolePermission(role_id=role.id, permission_id=permission.id)
                session.add(role_permission)
                await session.commit()

            return True


# 全局实例
_auth_manager: Optional[AuthManager] = None
_permission_manager: Optional[PermissionManager] = None


def get_auth_manager() -> AuthManager:
    """获取认证管理器实例"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
        logger.info("认证管理器已初始化")
    return _auth_manager


def get_permission_manager() -> PermissionManager:
    """获取权限管理器实例"""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
        logger.info("权限管理器已初始化")
    return _permission_manager


async def initialize_default_roles_and_permissions():
    """初始化默认角色和权限"""
    permission_manager = get_permission_manager()

    # 创建默认权限
    permissions = [
        {"name": "chat:access", "resource": "chat", "action": "access"},
        {"name": "chat:stream", "resource": "chat", "action": "stream"},
        {"name": "document:read", "resource": "document", "action": "read"},
        {"name": "document:create", "resource": "document", "action": "create"},
        {"name": "document:update", "resource": "document", "action": "update"},
        {"name": "document:delete", "resource": "document", "action": "delete"},
        {"name": "admin:user:manage", "resource": "admin", "action": "user_manage"},
        {"name": "admin:role:manage", "resource": "admin", "action": "role_manage"},
        {"name": "admin:permission:manage", "resource": "admin", "action": "permission_manage"},
    ]

    for perm in permissions:
        await permission_manager.create_permission(**perm)

    # 创建默认角色
    await permission_manager.create_role("admin", "系统管理员 - 拥有所有权限")
    await permission_manager.create_role("user", "普通用户 - 基础访问权限")

    # 为管理员角色分配所有权限
    await permission_manager.assign_permission_to_role("admin", "chat:access")
    await permission_manager.assign_permission_to_role("admin", "chat:stream")
    await permission_manager.assign_permission_to_role("admin", "document:read")
    await permission_manager.assign_permission_to_role("admin", "document:create")
    await permission_manager.assign_permission_to_role("admin", "document:update")
    await permission_manager.assign_permission_to_role("admin", "document:delete")
    await permission_manager.assign_permission_to_role("admin", "admin:user:manage")
    await permission_manager.assign_permission_to_role("admin", "admin:role:manage")
    await permission_manager.assign_permission_to_role("admin", "admin:permission:manage")

    # 为普通用户分配基础权限
    await permission_manager.assign_permission_to_role("user", "chat:access")
    await permission_manager.assign_permission_to_role("user", "chat:stream")
    await permission_manager.assign_permission_to_role("user", "document:read")

    logger.info("默认角色和权限初始化完成")
