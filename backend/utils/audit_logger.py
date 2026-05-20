"""
审计日志模块
提供完整的审计日志功能，支持：
- 记录所有关键操作
- 用户行为追踪
- 安全事件记录
- 操作审计查询
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import json
import uuid

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class AuditAction(Enum):
    """审计操作类型枚举"""
    # 用户管理
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_PASSWORD_CHANGE = "user_password_change"
    
    # 文档管理
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_UPDATE = "document_update"
    DOCUMENT_SHARE = "document_share"
    
    # 对话管理
    CONVERSATION_CREATE = "conversation_create"
    CONVERSATION_DELETE = "conversation_delete"
    MESSAGE_SEND = "message_send"
    
    # 权限管理
    ROLE_CREATE = "role_create"
    ROLE_UPDATE = "role_update"
    ROLE_DELETE = "role_delete"
    PERMISSION_ASSIGN = "permission_assign"
    PERMISSION_REVOKE = "permission_revoke"
    
    # 系统管理
    SYSTEM_CONFIG_UPDATE = "system_config_update"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    
    # 安全事件
    AUTH_FAILED = "auth_failed"
    ACCESS_DENIED = "access_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


from enum import Enum


@dataclass
class AuditRecord:
    """审计记录"""
    record_id: str
    user_id: Optional[int]
    action: AuditAction
    resource_type: str
    resource_id: Optional[int]
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    error_message: Optional[str]
    created_at: datetime

    def __post_init__(self):
        if not self.record_id:
            self.record_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "record_id": self.record_id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat()
        }


class AuditLogger:
    """审计日志记录器"""

    def __init__(self):
        self._records: List[AuditRecord] = []
        self._max_history = 5000  # 最大保留记录数
        self._enabled = True

    def enable(self):
        """启用审计日志"""
        self._enabled = True
        logger.info("审计日志已启用")

    def disable(self):
        """禁用审计日志"""
        self._enabled = False
        logger.info("审计日志已禁用")

    def log(self, action: AuditAction, resource_type: str, resource_id: Optional[int] = None,
            user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
            ip_address: Optional[str] = None, user_agent: Optional[str] = None,
            success: bool = True, error_message: Optional[str] = None):
        """记录审计日志"""
        if not self._enabled:
            return

        record = AuditRecord(
            record_id="",
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            created_at=datetime.now()
        )

        self._records.append(record)
        
        # 记录到普通日志
        logger.info(
            f"[审计] {action.value} | 用户:{user_id} | 资源:{resource_type}:{resource_id} | "
            f"成功:{success} | IP:{ip_address}"
        )

        # 清理旧记录
        self._cleanup_old_records()

    def get_records(self, user_id: Optional[int] = None, action: Optional[AuditAction] = None,
                    resource_type: Optional[str] = None, start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """查询审计记录"""
        records = self._records.copy()

        # 过滤
        if user_id is not None:
            records = [r for r in records if r.user_id == user_id]
        
        if action is not None:
            records = [r for r in records if r.action == action]
        
        if resource_type is not None:
            records = [r for r in records if r.resource_type == resource_type]
        
        if start_time is not None:
            records = [r for r in records if r.created_at >= start_time]
        
        if end_time is not None:
            records = [r for r in records if r.created_at <= end_time]

        # 排序
        records.sort(key=lambda r: r.created_at, reverse=True)

        # 限制数量
        return [r.to_dict() for r in records[:limit]]

    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """获取用户活动记录"""
        return self.get_records(user_id=user_id, limit=limit)

    def get_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取安全事件记录"""
        security_actions = [
            AuditAction.AUTH_FAILED,
            AuditAction.ACCESS_DENIED,
            AuditAction.SUSPICIOUS_ACTIVITY,
            AuditAction.USER_PASSWORD_CHANGE
        ]
        records = self._records.copy()
        records = [r for r in records if r.action in security_actions]
        records.sort(key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in records[:limit]]

    def get_summary(self, start_time: Optional[datetime] = None) -> Dict[str, Any]:
        """获取审计摘要"""
        records = self._records.copy()
        
        if start_time is not None:
            records = [r for r in records if r.created_at >= start_time]
        
        # 统计
        total_records = len(records)
        success_count = len([r for r in records if r.success])
        failed_count = len([r for r in records if not r.success])
        
        # 按操作类型统计
        action_counts: Dict[str, int] = {}
        for r in records:
            action_counts[r.action.value] = action_counts.get(r.action.value, 0) + 1
        
        # 按资源类型统计
        resource_counts: Dict[str, int] = {}
        for r in records:
            resource_counts[r.resource_type] = resource_counts.get(r.resource_type, 0) + 1

        return {
            "total_records": total_records,
            "success_count": success_count,
            "failed_count": failed_count,
            "action_counts": action_counts,
            "resource_counts": resource_counts
        }

    def _cleanup_old_records(self):
        """清理旧记录"""
        if len(self._records) > self._max_history:
            self._records = self._records[-self._max_history:]

    def export_records(self, file_path: str, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None):
        """导出审计记录到文件"""
        records = self.get_records(start_time=start_time, end_time=end_time)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        logger.info(f"审计记录已导出到: {file_path}")


# 全局审计日志记录器实例
audit_logger = AuditLogger()


def log_audit(action: str, resource_type: str, resource_id: Optional[int] = None,
              user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
              ip_address: Optional[str] = None, user_agent: Optional[str] = None,
              success: bool = True, error_message: Optional[str] = None):
    """记录审计日志（对外接口）"""
    try:
        action_enum = AuditAction[action.upper()]
    except KeyError:
        logger.warning(f"未知的审计操作类型: {action}")
        return
    
    audit_logger.log(
        action=action_enum,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message
    )


def get_audit_records(user_id: Optional[int] = None, action: Optional[str] = None,
                      resource_type: Optional[str] = None, start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """查询审计记录（对外接口）"""
    action_enum = None
    if action:
        try:
            action_enum = AuditAction[action.upper()]
        except KeyError:
            logger.warning(f"未知的审计操作类型: {action}")
    
    return audit_logger.get_records(
        user_id=user_id,
        action=action_enum,
        resource_type=resource_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )


def get_user_activity(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """获取用户活动记录（对外接口）"""
    return audit_logger.get_user_activity(user_id, limit)


def get_security_events(limit: int = 50) -> List[Dict[str, Any]]:
    """获取安全事件记录（对外接口）"""
    return audit_logger.get_security_events(limit)


def get_audit_summary(start_time: Optional[datetime] = None) -> Dict[str, Any]:
    """获取审计摘要（对外接口）"""
    return audit_logger.get_summary(start_time)