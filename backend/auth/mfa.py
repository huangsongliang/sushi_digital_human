"""双因素认证（MFA）模块"""

from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

import pyotp

from backend.models.database import db
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class MFAManager:
    """MFA 管理器"""

    def __init__(self):
        self.issuer_name = "SushiDigitalHuman"

    def generate_secret(self) -> str:
        """生成 TOTP 密钥"""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, user_email: str) -> str:
        """获取配置 URI（用于生成二维码）"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=user_email, issuer_name=self.issuer_name)

    def verify_totp(self, secret: str, token: str) -> bool:
        """验证 TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token)

    def generate_recovery_codes(self, count: int = 10) -> list:
        """生成恢复码"""
        import secrets

        recovery_codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            recovery_codes.append(code)
        return recovery_codes

    def enable_mfa(self, user_id: str, secret: str) -> bool:
        """启用 MFA"""
        try:
            mfa_id = str(uuid4())
            recovery_codes = self.generate_recovery_codes()
            recovery_codes_hash = ",".join(recovery_codes)

            db.execute(
                """
                INSERT INTO user_mfa (id, user_id, secret, recovery_codes, enabled, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE secret = %s, recovery_codes = %s, enabled = %s
                """,
                (mfa_id, user_id, secret, recovery_codes_hash, True, datetime.now(), secret, recovery_codes_hash, True),
            )
            db.commit()

            logger.info(f"MFA 已启用: user_id={user_id}")
            return True

        except Exception as e:
            logger.error(f"启用 MFA 失败: {str(e)}")
            db.rollback()
            return False

    def disable_mfa(self, user_id: str) -> bool:
        """禁用 MFA"""
        try:
            db.execute(
                """
                UPDATE user_mfa SET enabled = %s WHERE user_id = %s
                """,
                (False, user_id),
            )
            db.commit()
            logger.info(f"MFA 已禁用: user_id={user_id}")
            return True

        except Exception as e:
            logger.error(f"禁用 MFA 失败: {str(e)}")
            db.rollback()
            return False

    def is_mfa_enabled(self, user_id: str) -> bool:
        """检查 MFA 是否启用"""
        try:
            result = db.execute(
                """
                SELECT enabled FROM user_mfa WHERE user_id = %s
                """,
                (user_id,),
            )
            row = result.fetchone()
            return row[0] if row else False

        except Exception as e:
            logger.error(f"检查 MFA 状态失败: {str(e)}")
            return False

    def verify_and_consume_recovery_code(self, user_id: str, code: str) -> bool:
        """验证并使用恢复码"""
        try:
            result = db.execute(
                """
                SELECT recovery_codes FROM user_mfa WHERE user_id = %s AND enabled = %s
                """,
                (user_id, True),
            )
            row = result.fetchone()
            if not row:
                return False

            recovery_codes = row[0].split(",")
            if code.upper() in recovery_codes:
                recovery_codes.remove(code.upper())
                db.execute(
                    """
                    UPDATE user_mfa SET recovery_codes = %s WHERE user_id = %s
                    """,
                    (",".join(recovery_codes), user_id),
                )
                db.commit()
                logger.info(f"恢复码已使用: user_id={user_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"验证恢复码失败: {str(e)}")
            return False

    def get_user_mfa_status(self, user_id: str) -> Dict:
        """获取用户 MFA 状态"""
        try:
            result = db.execute(
                """
                SELECT enabled, created_at FROM user_mfa WHERE user_id = %s
                """,
                (user_id,),
            )
            row = result.fetchone()
            if row:
                return {
                    "enabled": row[0],
                    "created_at": str(row[1]),
                }
            return {"enabled": False}

        except Exception as e:
            logger.error(f"获取 MFA 状态失败: {str(e)}")
            return {"enabled": False}


_mfa_manager: Optional[MFAManager] = None


def get_mfa_manager() -> MFAManager:
    """获取 MFA 管理器实例"""
    global _mfa_manager
    if _mfa_manager is None:
        _mfa_manager = MFAManager()
        logger.info("MFA 管理器已初始化")
    return _mfa_manager
