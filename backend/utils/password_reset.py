"""用户密码重置模块"""

import uuid
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


@dataclass
class PasswordResetToken:
    """密码重置令牌"""

    token: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    used: bool = False

    def is_valid(self) -> bool:
        """检查令牌是否有效"""
        return (
            not self.used
            and datetime.now() < self.expires_at
        )

    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        return datetime.now() >= self.expires_at


class PasswordResetService:
    """密码重置服务"""

    TOKEN_EXPIRE_HOURS = 1

    def __init__(self):
        self._tokens = {}

    def generate_reset_token(self, user_id: str) -> PasswordResetToken:
        """生成密码重置令牌

        Args:
            user_id: 用户ID

        Returns:
            密码重置令牌
        """
        token = str(uuid.uuid4())
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=self.TOKEN_EXPIRE_HOURS)

        reset_token = PasswordResetToken(
            token=token,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at,
            used=False
        )

        self._tokens[token] = reset_token
        return reset_token

    def validate_token(self, token: str) -> tuple[bool, Optional[str]]:
        """验证重置令牌

        Args:
            token: 令牌

        Returns:
            (是否有效, 错误信息)
        """
        if token not in self._tokens:
            return False, "令牌不存在"

        reset_token = self._tokens[token]

        if reset_token.used:
            return False, "令牌已使用"

        if reset_token.is_expired():
            return False, "令牌已过期"

        return True, None

    def get_user_id(self, token: str) -> Optional[str]:
        """获取令牌对应的用户ID

        Args:
            token: 令牌

        Returns:
            用户ID或None
        """
        if token not in self._tokens:
            return None

        reset_token = self._tokens[token]
        if not reset_token.is_valid():
            return None

        return reset_token.user_id

    def mark_token_used(self, token: str) -> bool:
        """标记令牌已使用

        Args:
            token: 令牌

        Returns:
            是否成功
        """
        if token not in self._tokens:
            return False

        self._tokens[token].used = True
        return True

    def generate_reset_url(self, token: str, base_url: str) -> str:
        """生成密码重置链接

        Args:
            token: 令牌
            base_url: 基础URL

        Returns:
            重置链接
        """
        return f"{base_url}/reset-password?token={token}"


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """验证密码强度

    Args:
        password: 密码

    Returns:
        (是否有效, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8个字符"

    if len(password) > 128:
        return False, "密码长度不能超过128个字符"

    if not any(c.isupper() for c in password):
        return False, "密码必须包含至少一个大写字母"

    if not any(c.islower() for c in password):
        return False, "密码必须包含至少一个小写字母"

    if not any(c.isdigit() for c in password):
        return False, "密码必须包含至少一个数字"

    return True, None
