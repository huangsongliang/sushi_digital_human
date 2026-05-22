"""登录验证模块单元测试"""

import pytest
from backend.utils.login_validator import (
    LoginValidator,
    validate_user_login
)


class TestEmailValidation:
    """邮箱验证测试"""

    def test_valid_email(self):
        """测试有效邮箱"""
        assert LoginValidator.validate_email("user@example.com") is True

    def test_invalid_email_no_at(self):
        """测试无效邮箱（无@符号）"""
        assert LoginValidator.validate_email("userexample.com") is False

    def test_invalid_email_no_domain(self):
        """测试无效邮箱（无域名）"""
        assert LoginValidator.validate_email("user@") is False

    def test_invalid_email_empty(self):
        """测试空邮箱"""
        assert LoginValidator.validate_email("") is False


class TestPasswordValidation:
    """密码验证测试"""

    def test_valid_password(self):
        """测试有效密码"""
        is_valid, error = LoginValidator.validate_password("Pass1234")
        assert is_valid is True
        assert error is None

    def test_password_too_short(self):
        """测试密码太短"""
        is_valid, error = LoginValidator.validate_password("Pass1")
        assert is_valid is False
        assert "至少8个字符" in error

    def test_password_no_uppercase(self):
        """测试密码无大写字母"""
        is_valid, error = LoginValidator.validate_password("pass1234")
        assert is_valid is False
        assert "大写字母" in error

    def test_password_no_lowercase(self):
        """测试密码无小写字母"""
        is_valid, error = LoginValidator.validate_password("PASS1234")
        assert is_valid is False
        assert "小写字母" in error

    def test_password_no_digit(self):
        """测试密码无数字"""
        is_valid, error = LoginValidator.validate_password("Password")
        assert is_valid is False
        assert "数字" in error

    def test_password_empty(self):
        """测试空密码"""
        is_valid, error = LoginValidator.validate_password("")
        assert is_valid is False
        assert "不能为空" in error


class TestLoginValidation:
    """登录验证测试"""

    def test_valid_login(self):
        """测试有效登录"""
        is_valid, error = LoginValidator.validate_login(
            "user@example.com",
            "Pass1234"
        )
        assert is_valid is True
        assert error is None

    def test_invalid_email_login(self):
        """测试无效邮箱登录"""
        is_valid, error = LoginValidator.validate_login(
            "invalid-email",
            "Pass1234"
        )
        assert is_valid is False
        assert "邮箱格式" in error

    def test_invalid_password_login(self):
        """测试无效密码登录"""
        is_valid, error = LoginValidator.validate_login(
            "user@example.com",
            "weak"
        )
        assert is_valid is False


class TestValidateUserLogin:
    """用户登录验证接口测试"""

    def test_valid_input(self):
        """测试有效输入"""
        result = validate_user_login("user@example.com", "Pass1234")
        assert result["valid"] is True
        assert result["error"] is None
        assert result["email"] == "user@example.com"

    def test_invalid_input(self):
        """测试无效输入"""
        result = validate_user_login("invalid", "weak")
        assert result["valid"] is False
        assert result["error"] is not None
        assert result["email"] is None
