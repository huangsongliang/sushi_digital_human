"""短信服务模块"""

import asyncio
import random
from typing import Dict, Optional
from datetime import datetime, timedelta
from backend.utils.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)


class SmsService:
    """短信服务"""

    def __init__(self):
        self._code_store: Dict[str, Dict[str, str | datetime]] = {}
        self._send_lock: asyncio.Lock = asyncio.Lock()
        self._use_real_sms = settings.sms_use_real_service
        self._aliyun_config = {
            "access_key_id": settings.aliyun_access_key_id,
            "access_key_secret": settings.aliyun_access_key_secret,
            "sign_name": settings.sms_sign_name,
            "template_code": settings.sms_template_code,
            "region_id": settings.sms_region_id,
        }

    async def send_sms_code(self, phone: str) -> bool:
        """
        发送短信验证码

        Args:
            phone: 手机号码

        Returns:
            bool: 是否发送成功
        """
        async with self._send_lock:
            # 检查发送频率（1分钟内只能发送一次）
            if phone in self._code_store:
                last_send_time = self._code_store[phone].get("send_time")
                if last_send_time and datetime.now() - last_send_time < timedelta(minutes=1):
                    logger.warning(f"短信发送过于频繁: {phone}")
                    return False

            # 生成6位验证码
            code = self._generate_code()

            # 存储验证码（有效期5分钟）
            self._code_store[phone] = {
                "code": code,
                "send_time": datetime.now(),
                "expire_time": datetime.now() + timedelta(minutes=5),
            }

            # 根据配置选择发送方式
            if self._use_real_sms and all(self._aliyun_config.values()):
                success = await self._send_real_sms(phone, code)
            else:
                await self._simulate_send(phone, code)
                success = True

            if success:
                logger.info(f"验证码发送成功: {phone} -> {code}")
            return success

    def verify_sms_code(self, phone: str, code: str) -> bool:
        """
        验证短信验证码

        Args:
            phone: 手机号码
            code: 验证码

        Returns:
            bool: 是否验证通过
        """
        if phone not in self._code_store:
            logger.warning(f"验证码不存在: {phone}")
            return False

        stored = self._code_store[phone]

        # 检查是否过期
        if datetime.now() > stored["expire_time"]:
            logger.warning(f"验证码已过期: {phone}")
            del self._code_store[phone]
            return False

        # 检查验证码是否匹配
        if stored["code"] != code:
            logger.warning(f"验证码错误: {phone}")
            return False

        # 验证成功后删除验证码（一次性使用）
        del self._code_store[phone]
        logger.info(f"验证码验证成功: {phone}")
        return True

    def _generate_code(self) -> str:
        """生成6位数字验证码"""
        return "".join(random.choices("0123456789", k=6))

    async def _simulate_send(self, phone: str, code: str):
        """模拟发送短信（开发测试用）"""
        await asyncio.sleep(0.5)
        logger.info(f"【模拟发送短信】手机号: {phone}, 验证码: {code}")

    async def _send_real_sms(self, phone: str, code: str) -> bool:
        """发送真实短信（阿里云）"""
        try:
            from aliyunsdkcore.client import AcsClient
            from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest

            client = AcsClient(
                self._aliyun_config["access_key_id"],
                self._aliyun_config["access_key_secret"],
                self._aliyun_config["region_id"],
            )

            request = SendSmsRequest.SendSmsRequest()
            request.set_accept_format("json")
            request.set_PhoneNumbers(phone)
            request.set_SignName(self._aliyun_config["sign_name"])
            request.set_TemplateCode(self._aliyun_config["template_code"])
            request.set_TemplateParam(f'{{"code":"{code}"}}')

            response = client.do_action_with_exception(request)
            logger.info(f"【真实短信发送】手机号: {phone}, 响应: {response}")
            return True

        except ImportError:
            logger.error("未安装阿里云SDK，请运行: uv pip install aliyun-python-sdk-core aliyun-python-sdk-dysmsapi")
            return False
        except Exception as e:
            logger.error(f"【真实短信发送失败】手机号: {phone}, 错误: {str(e)}")
            return False


# 全局实例
_sms_service: Optional[SmsService] = None


def get_sms_service() -> SmsService:
    """获取短信服务实例"""
    global _sms_service
    if _sms_service is None:
        _sms_service = SmsService()
        logger.info("短信服务已初始化")
    return _sms_service
