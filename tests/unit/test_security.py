"""安全模块单元测试"""
import pytest


class TestSecurityModule:
    """安全模块测试"""

    def test_security_module_import(self):
        try:
            from backend.core.security import (
                verify_password,
                get_password_hash
            )
            assert verify_password is not None
            assert get_password_hash is not None
        except ImportError:
            pytest.skip("Security dependencies not installed")

    def test_password_hashing(self):
        try:
            from backend.core.security import (
                verify_password,
                get_password_hash
            )

            password = "test_password_123"
            hashed = get_password_hash(password)
            assert hashed is not None
            assert len(hashed) > 0
            assert verify_password(password, hashed) is True
            assert verify_password("wrong_password", hashed) is False
        except ImportError:
            pytest.skip("Security dependencies not installed")
