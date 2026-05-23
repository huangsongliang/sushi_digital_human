"""审计日志模块单元测试"""

from datetime import datetime

from backend.utils.audit_logger import AuditAction, AuditRecord


class TestAuditAction:
    """AuditAction 枚举测试"""

    def test_enum_values(self):
        assert AuditAction.USER_LOGIN.value == "user_login"
        assert AuditAction.USER_LOGOUT.value == "user_logout"
        assert AuditAction.USER_CREATE.value == "user_create"
        assert AuditAction.DOCUMENT_UPLOAD.value == "document_upload"
        assert AuditAction.AUTH_FAILED.value == "auth_failed"

    def test_enum_membership(self):
        assert AuditAction("user_login") == AuditAction.USER_LOGIN
        assert AuditAction("auth_failed") == AuditAction.AUTH_FAILED


class TestAuditRecord:
    """AuditRecord 测试"""

    def test_record_creation(self):
        record = AuditRecord(
            record_id="r1",
            user_id=1,
            action=AuditAction.USER_LOGIN,
            resource_type="user",
            resource_id=1,
            details={"ip": "127.0.0.1"},
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=True,
            error_message=None,
            created_at=datetime.now(),
        )
        assert record.record_id == "r1"
        assert record.user_id == 1
        assert record.action == AuditAction.USER_LOGIN
        assert record.success is True
        assert record.error_message is None

    def test_record_to_dict(self):
        record = AuditRecord(
            record_id="r1",
            user_id=1,
            action=AuditAction.USER_LOGIN,
            resource_type="user",
            resource_id=1,
            details={"ip": "127.0.0.1"},
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=True,
            error_message=None,
            created_at=datetime.now(),
        )
        data = record.to_dict()
        assert data["record_id"] == "r1"
        assert data["action"] == "user_login"
        assert data["success"] is True
        assert data["details"] == {"ip": "127.0.0.1"}

    def test_record_with_error(self):
        record = AuditRecord(
            record_id="r2",
            user_id=1,
            action=AuditAction.AUTH_FAILED,
            resource_type="auth",
            resource_id=1,
            details={},
            ip_address=None,
            user_agent=None,
            success=False,
            error_message="Invalid credentials",
            created_at=datetime.now(),
        )
        assert record.success is False
        assert record.error_message == "Invalid credentials"

    def test_record_defaults(self):
        record = AuditRecord(
            record_id="",
            user_id=None,
            action=AuditAction.USER_LOGOUT,
            resource_type="session",
            resource_id=None,
            details={},
            ip_address=None,
            user_agent=None,
            success=True,
            error_message=None,
            created_at=None,
        )
        # __post_init__ 会生成 record_id 和 created_at
        assert record.record_id != ""
        assert record.created_at is not None
        assert record.ip_address is None
        assert record.user_agent is None
