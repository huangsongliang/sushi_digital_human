"""用户登录验证模块"""

import re
from typing import Optional


class LoginValidationError(Exception):
    """登录验证异常"""


class LoginValidator:
    """用户登录验证器"""

    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """验证邮箱格式

        Args:
            email: 邮箱地址

        Returns:
            是否有效
        """
        if not email:
            return False
        return bool(cls.EMAIL_PATTERN.match(email))

    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, Optional[str]]:
        """验证密码强度

        Args:
            password: 密码

        Returns:
            (是否有效, 错误信息)
        """
        if not password:
            return False, "密码不能为空"

        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return (False, f"密码长度至少{cls.MIN_PASSWORD_LENGTH}个字符")

        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return (False, f"密码长度不能超过{cls.MAX_PASSWORD_LENGTH}个字符")

        if not re.search(r"[A-Z]", password):
            return False, "密码必须包含至少一个大写字母"

        if not re.search(r"[a-z]", password):
            return False, "密码必须包含至少一个小写字母"

        if not re.search(r"[0-9]", password):
            return False, "密码必须包含至少一个数字"

        return True, None

    @classmethod
    def validate_login(cls, email: str, password: str) -> tuple[bool, Optional[str]]:
        """验证登录信息

        Args:
            email: 邮箱地址
            password: 密码

        Returns:
            (是否有效, 错误信息)
        """
        if not cls.validate_email(email):
            return False, "邮箱格式不正确"

        is_valid, error_msg = cls.validate_password(password)
        if not is_valid:
            return False, error_msg

        return True, None


def validate_user_login(email: str, password: str) -> dict:
    """用户登录验证接口

    Args:
        email: 邮箱地址
        password: 密码

    Returns:
        验证结果字典
    """
    validator = LoginValidator()
    is_valid, error_msg = validator.validate_login(email, password)

    return {"valid": is_valid, "error": error_msg, "email": email if is_valid else None}
