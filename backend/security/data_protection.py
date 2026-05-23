"""数据加密和脱敏模块"""

import hashlib
import re
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionManager:
    """数据加密管理器"""

    def __init__(self, key: Optional[bytes] = None):
        if key:
            self.fernet = Fernet(key)
        elif settings.encryption_key:
            self.fernet = Fernet(settings.encryption_key.encode())
        else:
            self.fernet = None

    @staticmethod
    def generate_key(password: str, salt: bytes) -> bytes:
        """生成加密密钥"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    @staticmethod
    def generate_salt() -> bytes:
        """生成盐值"""
        import os
        return os.urandom(16)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        if not self.fernet:
            raise RuntimeError("加密器未初始化")

        encrypted = self.fernet.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        if not self.fernet:
            raise RuntimeError("加密器未初始化")

        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(encrypted_bytes)
        return decrypted.decode()


class DataMasking:
    """数据脱敏处理器"""

    PHONE_PATTERN = re.compile(r'(\d{3})\d{4}(\d{4})')
    EMAIL_PATTERN = re.compile(r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
    ID_CARD_PATTERN = re.compile(r'(\d{6})\d{8}(\d{4})')
    BANK_CARD_PATTERN = re.compile(r'(\d{4})\d{11,15}(\d{4})')
    IP_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.)(\d{1,3})')

    def mask_phone(self, phone: str) -> str:
        """脱敏手机号"""
        return self.PHONE_PATTERN.sub(r'\1****\2', phone)

    def mask_email(self, email: str) -> str:
        """脱敏邮箱"""
        match = self.EMAIL_PATTERN.match(email)
        if match:
            username, domain = match.groups()
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1] if len(username) > 2 else username
            return f"{masked_username}@{domain}"
        return email

    def mask_id_card(self, id_card: str) -> str:
        """脱敏身份证"""
        return self.ID_CARD_PATTERN.sub(r'\1********\2', id_card)

    def mask_bank_card(self, card_number: str) -> str:
        """脱敏银行卡号"""
        return self.BANK_CARD_PATTERN.sub(r'\1****\2', card_number)

    def mask_ip(self, ip: str) -> str:
        """脱敏 IP 地址"""
        return self.IP_PATTERN.sub(r'\1*', ip)

    def mask_name(self, name: str) -> str:
        """脱敏姓名"""
        if len(name) == 2:
            return name[0] + '*'
        elif len(name) > 2:
            return name[0] + '*' * (len(name) - 2) + name[-1]
        return name

    def hash_sensitive_data(self, data: str, algorithm: str = 'sha256') -> str:
        """哈希敏感数据"""
        if algorithm == 'md5':
            return hashlib.md5(data.encode()).hexdigest()
        elif algorithm == 'sha1':
            return hashlib.sha1(data.encode()).hexdigest()
        elif algorithm == 'sha256':
            return hashlib.sha256(data.encode()).hexdigest()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")

    def mask_dict(self, data: Dict[str, Any], sensitive_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """对字典中的敏感字段进行脱敏"""
        if sensitive_fields is None:
            sensitive_fields = ['phone', 'email', 'id_card', 'bank_card', 'ip', 'name', 'password']

        masked_data = data.copy()

        for key, value in masked_data.items():
            if key in sensitive_fields and value:
                if isinstance(value, str):
                    if 'phone' in key.lower():
                        masked_data[key] = self.mask_phone(value)
                    elif 'email' in key.lower():
                        masked_data[key] = self.mask_email(value)
                    elif 'id' in key.lower() and 'card' in key.lower():
                        masked_data[key] = self.mask_id_card(value)
                    elif 'bank' in key.lower() or 'card' in key.lower():
                        masked_data[key] = self.mask_bank_card(value)
                    elif 'ip' in key.lower():
                        masked_data[key] = self.mask_ip(value)
                    elif 'name' in key.lower():
                        masked_data[key] = self.mask_name(value)
                    elif 'password' in key.lower():
                        masked_data[key] = '********'

        return masked_data

    def auto_detect_and_mask(self, text: str) -> str:
        """自动检测并脱敏文本中的敏感信息"""
        masked_text = text
        masked_text = self.PHONE_PATTERN.sub(r'\1****\2', masked_text)
        masked_text = self.EMAIL_PATTERN.sub(
            lambda m: m.group(1)[0] + '***@' + m.group(2), masked_text
        )
        masked_text = self.ID_CARD_PATTERN.sub(r'\1********\2', masked_text)
        masked_text = self.BANK_CARD_PATTERN.sub(r'\1****\2', masked_text)
        masked_text = self.IP_PATTERN.sub(r'\1*', masked_text)
        return masked_text


_encryption_manager: Optional[EncryptionManager] = None
_data_masking: Optional[DataMasking] = None


def get_encryption_manager() -> EncryptionManager:
    """获取加密管理器实例"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
        logger.info("加密管理器已初始化")
    return _encryption_manager


def get_data_masking() -> DataMasking:
    """获取数据脱敏处理器实例"""
    global _data_masking
    if _data_masking is None:
        _data_masking = DataMasking()
        logger.info("数据脱敏处理器已初始化")
    return _data_masking
