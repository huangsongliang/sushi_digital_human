"""密码重置模块单元测试"""

import pytest
from datetime import datetime, timedelta
from backend.utils.password_reset import (
    PasswordResetToken,
    PasswordResetService,
    validate_password_strength
)


class TestPasswordResetToken:
    """密码重置令牌测试"""

    def test_token_is_valid(self):
        """测试有效令牌"""
        token = PasswordResetToken(
            token="test-token",
            user_id="user-123",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            used=False
        )
        assert token.is_valid() is True

    def test_token_is_used(self):
        """测试已使用的令牌"""
        token = PasswordResetToken(
            token="test-token",
            user_id="user-123",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            used=True
        )
        assert token.is_valid() is False

    def test_token_is_expired(self):
        """测试过期的令牌"""
        token = PasswordResetToken(
            token="test-token",
            user_id="user-123",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
            used=False
        )
        assert token.is_valid() is False
        assert token.is_expired() is True


class TestPasswordResetService:
    """密码重置服务测试"""

    def test_generate_reset_token(self):
        """测试生成重置令牌"""
        service = PasswordResetService()
        token = service.generate_reset_token("user-123")

        assert token.user_id == "user-123"
        assert token.is_valid() is True
        assert token.expires_at > datetime.now()

    def test_validate_valid_token(self):
        """测试验证有效令牌"""
        service = PasswordResetService()
        token = service.generate_reset_token("user-123")

        is_valid, error = service.validate_token(token.token)
        assert is_valid is True
        assert error is None

    def test_validate_invalid_token(self):
        """测试验证无效令牌"""
        service = PasswordResetService()

        is_valid, error = service.validate_token("invalid-token")
        assert is_valid is False
        assert "不存在" in error

    def test_validate_used_token(self):
        """测试验证已使用的令牌"""
        service = PasswordResetService()
        token = service.generate_reset_token("user-123")
        service.mark_token_used(token.token)

        is_valid, error = service.validate_token(token.token)
        assert is_valid is False
        assert "已使用" in error

    def test_generate_reset_url(self):
        """测试生成重置链接"""
        service = PasswordResetService()
        token = service.generate_reset_token("user-123")

        url = service.generate_reset_url(token.token, "https://example.com")
        assert "https://example.com/reset-password" in url
        assert token.token in url


class TestValidatePasswordStrength:
    """密码强度验证测试"""

    def test_valid_password(self):
        """测试有效密码"""
        is_valid, error = validate_password_strength("Pass1234")
        assert is_valid is True
        assert error is None

    def test_password_too_short(self):
        """测试密码太短"""
        is_valid, error = validate_password_strength("Pass1")
        assert is_valid is False
        assert "至少8个字符" in error

    def test_password_no_uppercase(self):
        """测试密码无大写字母"""
        is_valid, error = validate_password_strength("pass1234")
        assert is_valid is False
        assert "大写字母" in error

    def test_password_no_lowercase(self):
        """测试密码无小写字母"""
        is_valid, error = validate_password_strength("PASS1234")
        assert is_valid is False
        assert "小写字母" in error

    def test_password_no_digit(self):
        """测试密码无数字"""
        is_valid, error = validate_password_strength("Password")
        assert is_valid is False
        assert "数字" in error
