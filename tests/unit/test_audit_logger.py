"""审计日志模块单元测试"""

import pytest
from backend.utils.audit_logger import AuditAction, AuditRecord


class TestAuditAction:
    """AuditAction 枚举测试"""

    def test_enum_values(self):
        assert AuditAction.LOGIN.value == "login"
        assert AuditAction.LOGOUT.value == "logout"
        assert AuditAction.CREATE_USER.value == "create_user"
        assert AuditAction.UPLOAD_DOCUMENT.value == "upload_document"
        assert AuditAction.AUTH_FAILED.value == "auth_failed"

    def test_enum_membership(self):
        assert AuditAction("login") == AuditAction.LOGIN
        assert AuditAction("auth_failed") == AuditAction.AUTH_FAILED


class TestAuditRecord:
    """AuditRecord 测试"""

    def test_record_creation(self):
        record = AuditRecord(
            record_id="r1",
            user_id="u1",
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id="u1",
            success=True,
        )
        assert record.record_id == "r1"
        assert record.user_id == "u1"
        assert record.action == AuditAction.LOGIN
        assert record.success is True
        assert record.error_message is None

    def test_record_to_dict(self):
        record = AuditRecord(
            record_id="r1",
            user_id="u1",
            action=AuditAction.LOGIN,
            resource_type="user",
            resource_id="u1",
            details={"ip": "127.0.0.1"},
            success=True,
        )
        data = record.to_dict()
        assert data["record_id"] == "r1"
        assert data["action"] == "login"
        assert data["success"] is True
        assert data["details"] == {"ip": "127.0.0.1"}

    def test_record_with_error(self):
        record = AuditRecord(
            record_id="r2",
            user_id="u1",
            action=AuditAction.AUTH_FAILED,
            resource_type="auth",
            resource_id="u1",
            success=False,
            error_message="Invalid credentials",
        )
        assert record.success is False
        assert record.error_message == "Invalid credentials"

    def test_record_defaults(self):
        record = AuditRecord(
            record_id="r3",
            user_id="u1",
            action=AuditAction.LOGOUT,
            resource_type="session",
            resource_id="s1",
        )
        assert record.success is True
        assert record.details == {}
        assert record.ip_address == ""
        assert record.user_agent == ""
        assert record.created_at is not None
