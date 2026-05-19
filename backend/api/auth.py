"""用户认证与权限管理 API"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

from backend.core.auth_manager import get_auth_manager, get_permission_manager
from backend.core.security import verify_token
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    """用户登录请求"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: str
    roles: List[str]
    permissions: List[str]


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class AssignRoleRequest(BaseModel):
    """分配角色请求"""
    user_id: int
    role_name: str


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """获取当前用户ID"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
        )

    try:
        payload = verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌无效",
            )
        return int(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )


async def require_permission(permission_name: str):
    """权限依赖装饰器"""
    async def dependency(user_id: int = Depends(get_current_user_id)):
        permission_manager = get_permission_manager()
        has_perm = await permission_manager.has_permission(user_id, permission_name)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"缺少权限: {permission_name}",
            )
        return user_id
    return dependency


@router.post("/register")
async def register(request: RegisterRequest):
    """用户注册"""
    auth_manager = get_auth_manager()
    result = await auth_manager.register_user(
        username=request.username,
        email=request.email,
        password=request.password,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return {"message": "注册成功", "user_id": result.get("user_id")}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """用户登录"""
    auth_manager = get_auth_manager()
    result = await auth_manager.login_user(
        email=request.email,
        password=request.password,
    )

    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))

    return TokenResponse(
        access_token=result.get("access_token"),
        refresh_token=result.get("refresh_token"),
    )


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    """刷新访问令牌"""
    auth_manager = get_auth_manager()
    result = await auth_manager.refresh_token(request.refresh_token)

    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error"))

    return TokenResponse(access_token=result.get("access_token"))


@router.get("/me", response_model=UserInfo)
async def get_current_user(user_id: int = Depends(get_current_user_id)):
    """获取当前用户信息"""
    auth_manager = get_auth_manager()
    permission_manager = get_permission_manager()

    user = await auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    roles = await permission_manager.get_user_roles(user_id)
    permissions = await permission_manager.get_user_permissions(user_id)

    return UserInfo(
        id=user.id,
        username=user.username,
        email=user.email,
        roles=roles,
        permissions=permissions,
    )


@router.post("/roles/assign")
async def assign_role(
    request: AssignRoleRequest,
    user_id: int = Depends(require_permission("admin:user:manage")),
):
    """为用户分配角色（需要管理员权限）"""
    permission_manager = get_permission_manager()
    success = await permission_manager.assign_role_to_user(
        user_id=request.user_id,
        role_name=request.role_name,
    )

    if not success:
        raise HTTPException(status_code=400, detail="分配角色失败")

    return {"message": "角色分配成功"}


@router.get("/roles")
async def list_roles(user_id: int = Depends(get_current_user_id)):
    """获取所有角色列表"""
    from backend.database.session import get_db_session
    from backend.database.models import Role
    from sqlalchemy import select

    async with get_db_session() as session:
        result = await session.execute(select(Role))
        roles = result.scalars().all()

        return [
            {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            }
            for role in roles
        ]


@router.get("/permissions")
async def list_permissions(user_id: int = Depends(get_current_user_id)):
    """获取所有权限列表"""
    from backend.database.session import get_db_session
    from backend.database.models import Permission
    from sqlalchemy import select

    async with get_db_session() as session:
        result = await session.execute(select(Permission))
        permissions = result.scalars().all()

        return [
            {
                "id": perm.id,
                "name": perm.name,
                "description": perm.description,
                "resource": perm.resource,
                "action": perm.action,
            }
            for perm in permissions
        ]
