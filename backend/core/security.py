"""
安全工具模块
提供认证、授权、加密等安全功能：
- JWT 令牌生成与验证
- 密码哈希
- API 限流
- 输入验证与清洗
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# 密码哈希配置 - 使用 Argon2id（2015年密码哈希大赛冠军，OWASP推荐）
# 参数配置遵循 OWASP 推荐标准：
# - memory_cost: 至少 65536 (64MB)
# - time_cost: 至少 3 次迭代
# - parallelism: 至少 4 线程
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)

# Bearer Token 安全方案
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希（使用 Argon2id 算法）

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌（JWT）

    Args:
        data: 要编码到令牌中的数据
        expires_delta: 令牌过期时间

    Returns:
        str: 编码后的 JWT 令牌
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    验证 JWT 令牌

    Args:
        token: JWT 令牌字符串

    Returns:
        Dict[str, Any]: 解码后的令牌数据

    Raises:
        HTTPException: 令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError as e:
        logger.warning(f"JWT 验证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    """
    从令牌中获取当前用户 ID

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        Optional[str]: 用户 ID，如果未提供令牌则返回 None
    """
    if credentials is None:
        return None

    try:
        payload = verify_token(credentials.credentials)
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except HTTPException:
        return None


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    清洗用户输入，防止 XSS 和注入攻击

    Args:
        text: 用户输入文本
        max_length: 最大允许长度

    Returns:
        str: 清洗后的文本
    """
    if not text:
        return ""

    # 限制长度
    text = text[:max_length]

    # 移除潜在的 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    # 移除控制字符
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\r\t")

    return text.strip()


def check_rate_limit(request: Request) -> None:
    """
    检查 API 调用频率限制

    Args:
        request: FastAPI 请求对象

    Raises:
        HTTPException: 超出限流阈值
    """
    client_ip = request.client.host if request.client else "unknown"

    # 这里应该使用 Redis 实现真正的限流
    # 当前为占位实现，后续接入 Redis 后完善
    logger.debug(f"Rate limit check for {client_ip}")

    # TODO: 实现基于 Redis 的限流逻辑
    # 示例：
    # key = f"rate_limit:{client_ip}"
    # current = redis_client.incr(key)
    # if current == 1:
    #     redis_client.expire(key, 60)
    # if current > settings.rate_limit_per_minute:
    #     raise HTTPException(
    #         status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    #         detail="请求过于频繁，请稍后再试"
    #     )


class OptionalBearerAuth(HTTPBearer):
    """
    可选的 Bearer 认证
    如果未提供令牌也不会抛出异常
    """

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        return await super().__call__(request)
