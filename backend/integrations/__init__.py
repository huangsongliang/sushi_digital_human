"""
应用集成模块
提供企业应用集成功能，支持：
- 钉钉机器人消息推送
- 企业微信机器人消息推送
- Slack 消息推送
- Webhook 集成
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class IntegrationType(Enum):
    """集成类型枚举"""

    DINGTALK = "dingtalk"
    WECOM = "wecom"
    SLACK = "slack"
    WEBHOOK = "webhook"


class MessageType(Enum):
    """消息类型枚举"""

    TEXT = "text"
    MARKDOWN = "markdown"
    LINK = "link"
    CARD = "card"


@dataclass
class IntegrationConfig:
    """集成配置"""

    type: IntegrationType
    name: str
    webhook_url: str
    enabled: bool = True
    secret: Optional[str] = None
    additional_config: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}


@dataclass
class MessageResult:
    """消息发送结果"""

    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None


class BaseIntegration(ABC):
    """集成基类"""

    def __init__(self, config: IntegrationConfig):
        self._config = config
        self._enabled = config.enabled

    @abstractmethod
    async def send_text(self, content: str, **kwargs) -> MessageResult:
        """发送文本消息"""

    @abstractmethod
    async def send_markdown(self, content: str, title: Optional[str] = None, **kwargs) -> MessageResult:
        """发送 Markdown 消息"""

    @abstractmethod
    async def send_link(self, title: str, text: str, url: str, pic_url: Optional[str] = None) -> MessageResult:
        """发送链接消息"""

    @abstractmethod
    async def send_card(self, card_data: Dict[str, Any]) -> MessageResult:
        """发送卡片消息"""

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

    def enable(self):
        """启用集成"""
        self._enabled = True
        self._config.enabled = True

    def disable(self):
        """禁用集成"""
        self._enabled = False
        self._config.enabled = False

    def get_config(self) -> IntegrationConfig:
        """获取配置"""
        return self._config


class DingTalkIntegration(BaseIntegration):
    """钉钉集成"""

    async def send_text(self, content: str, at_users: Optional[List[str]] = None, **kwargs) -> MessageResult:
        """发送文本消息"""
        try:
            import base64
            import hashlib
            import hmac
            import time
            import urllib.parse

            import aiohttp

            timestamp = str(round(time.time() * 1000))
            webhook_url = self._config.webhook_url

            # 签名处理
            if self._config.secret:
                secret_enc = self._config.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self._config.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {
                "msgtype": "text",
                "text": {"content": content},
            }

            if at_users:
                payload["at"] = {"atMobiles": at_users}

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("messageId"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"钉钉发送消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_markdown(self, content: str, title: Optional[str] = None, **kwargs) -> MessageResult:
        """发送 Markdown 消息"""
        try:
            import base64
            import hashlib
            import hmac
            import time
            import urllib.parse

            import aiohttp

            timestamp = str(round(time.time() * 1000))
            webhook_url = self._config.webhook_url

            if self._config.secret:
                secret_enc = self._config.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self._config.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {"msgtype": "markdown", "markdown": {"title": title or "消息通知", "text": content}}

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("messageId"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"钉钉发送 Markdown 消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_link(self, title: str, text: str, url: str, pic_url: Optional[str] = None) -> MessageResult:
        """发送链接消息"""
        try:
            import base64
            import hashlib
            import hmac
            import time
            import urllib.parse

            import aiohttp

            timestamp = str(round(time.time() * 1000))
            webhook_url = self._config.webhook_url

            if self._config.secret:
                secret_enc = self._config.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self._config.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {
                "msgtype": "link",
                "link": {"text": text, "title": title, "picUrl": pic_url or "", "messageUrl": url},
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("messageId"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"钉钉发送链接消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_card(self, card_data: Dict[str, Any]) -> MessageResult:
        """发送卡片消息"""
        try:
            import base64
            import hashlib
            import hmac
            import time
            import urllib.parse

            import aiohttp

            timestamp = str(round(time.time() * 1000))
            webhook_url = self._config.webhook_url

            if self._config.secret:
                secret_enc = self._config.secret.encode("utf-8")
                string_to_sign = f"{timestamp}\n{self._config.secret}"
                string_to_sign_enc = string_to_sign.encode("utf-8")
                hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
                webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

            payload = {"msgtype": "actionCard", "actionCard": card_data}

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("messageId"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"钉钉发送卡片消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))


class WeComIntegration(BaseIntegration):
    """企业微信集成"""

    async def send_text(self, content: str, at_users: Optional[List[str]] = None, **kwargs) -> MessageResult:
        """发送文本消息"""
        try:
            import aiohttp

            payload = {"msgtype": "text", "text": {"content": content}}

            if at_users:
                payload["text"]["mentioned_list"] = at_users

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("msgid"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"企业微信发送消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_markdown(self, content: str, title: Optional[str] = None, **kwargs) -> MessageResult:
        """发送 Markdown 消息"""
        try:
            import aiohttp

            payload = {"msgtype": "markdown", "markdown": {"content": content}}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("msgid"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"企业微信发送 Markdown 消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_link(self, title: str, text: str, url: str, pic_url: Optional[str] = None) -> MessageResult:
        """发送链接消息"""
        try:
            import aiohttp

            payload = {
                "msgtype": "news",
                "news": {"articles": [{"title": title, "description": text, "url": url, "picurl": pic_url or ""}]},
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("msgid"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"企业微信发送链接消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_card(self, card_data: Dict[str, Any]) -> MessageResult:
        """发送卡片消息"""
        try:
            import aiohttp

            payload = {"msgtype": "template_card", "template_card": card_data}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return MessageResult(success=True, message_id=result.get("msgid"))
                    else:
                        return MessageResult(success=False, error_message=result.get("errmsg"))

        except Exception as e:
            logger.error(f"企业微信发送卡片消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))


class SlackIntegration(BaseIntegration):
    """Slack 集成"""

    async def send_text(self, content: str, channel: Optional[str] = None, **kwargs) -> MessageResult:
        """发送文本消息"""
        try:
            import aiohttp

            payload = {"text": content}
            if channel:
                payload["channel"] = channel

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.text()
                    if result == "ok":
                        return MessageResult(success=True)
                    else:
                        return MessageResult(success=False, error_message=result)

        except Exception as e:
            logger.error(f"Slack 发送消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_markdown(self, content: str, title: Optional[str] = None, **kwargs) -> MessageResult:
        """发送 Markdown 消息"""
        return await self.send_text(content, **kwargs)

    async def send_link(
        self, title: str, text: str, url: str, pic_url: Optional[str] = None, **kwargs
    ) -> MessageResult:
        """发送链接消息"""
        content = f"**{title}**\n{text}\n{url}"
        return await self.send_text(content)

    async def send_card(self, card_data: Dict[str, Any]) -> MessageResult:
        """发送卡片消息"""
        try:
            import aiohttp

            payload = {"attachments": [card_data]}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.text()
                    if result == "ok":
                        return MessageResult(success=True)
                    else:
                        return MessageResult(success=False, error_message=result)

        except Exception as e:
            logger.error(f"Slack 发送卡片消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))


class WebhookIntegration(BaseIntegration):
    """通用 Webhook 集成"""

    async def send_text(self, content: str, **kwargs) -> MessageResult:
        """发送文本消息"""
        try:
            import aiohttp

            payload = {"type": "text", "content": content, **kwargs}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    return MessageResult(success=True, response_data=result)

        except Exception as e:
            logger.error(f"Webhook 发送消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_markdown(self, content: str, title: Optional[str] = None, **kwargs) -> MessageResult:
        """发送 Markdown 消息"""
        try:
            import aiohttp

            payload = {"type": "markdown", "title": title or "", "content": content, **kwargs}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    return MessageResult(success=True, response_data=result)

        except Exception as e:
            logger.error(f"Webhook 发送 Markdown 消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_link(self, title: str, text: str, url: str, pic_url: Optional[str] = None) -> MessageResult:
        """发送链接消息"""
        try:
            import aiohttp

            payload = {
                "type": "link",
                "title": title,
                "text": text,
                "url": url,
                "pic_url": pic_url,
                **self._config.additional_config,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    return MessageResult(success=True, response_data=result)

        except Exception as e:
            logger.error(f"Webhook 发送链接消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_card(self, card_data: Dict[str, Any]) -> MessageResult:
        """发送卡片消息"""
        try:
            import aiohttp

            payload = {"type": "card", "data": card_data}

            async with aiohttp.ClientSession() as session:
                async with session.post(self._config.webhook_url, json=payload) as response:
                    result = await response.json()
                    return MessageResult(success=True, response_data=result)

        except Exception as e:
            logger.error(f"Webhook 发送卡片消息失败: {str(e)}")
            return MessageResult(success=False, error_message=str(e))


class IntegrationManager:
    """集成管理器"""

    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._configs: Dict[str, IntegrationConfig] = {}

    def register_integration(self, config: IntegrationConfig):
        """注册集成"""
        integration = self._create_integration(config)
        if integration:
            self._integrations[config.name] = integration
            self._configs[config.name] = config
            logger.info(f"已注册集成: {config.name} ({config.type.value})")

    def _create_integration(self, config: IntegrationConfig) -> Optional[BaseIntegration]:
        """根据配置创建集成实例"""
        try:
            if config.type == IntegrationType.DINGTALK:
                return DingTalkIntegration(config)
            elif config.type == IntegrationType.WECOM:
                return WeComIntegration(config)
            elif config.type == IntegrationType.SLACK:
                return SlackIntegration(config)
            elif config.type == IntegrationType.WEBHOOK:
                return WebhookIntegration(config)
            else:
                logger.warning(f"未知的集成类型: {config.type}")
                return None
        except Exception as e:
            logger.error(f"创建集成失败: {str(e)}")
            return None

    def get_integration(self, name: str) -> Optional[BaseIntegration]:
        """获取集成实例"""
        return self._integrations.get(name)

    def get_all_integrations(self) -> List[BaseIntegration]:
        """获取所有集成"""
        return list(self._integrations.values())

    def get_integration_config(self, name: str) -> Optional[IntegrationConfig]:
        """获取集成配置"""
        return self._configs.get(name)

    def get_all_configs(self) -> List[IntegrationConfig]:
        """获取所有配置"""
        return list(self._configs.values())

    async def send_message(self, name: str, message_type: MessageType, **kwargs) -> MessageResult:
        """发送消息"""
        integration = self._integrations.get(name)
        if not integration:
            return MessageResult(success=False, error_message=f"集成不存在: {name}")

        if not integration.is_enabled():
            return MessageResult(success=False, error_message=f"集成未启用: {name}")

        try:
            if message_type == MessageType.TEXT:
                return await integration.send_text(**kwargs)
            elif message_type == MessageType.MARKDOWN:
                return await integration.send_markdown(**kwargs)
            elif message_type == MessageType.LINK:
                return await integration.send_link(**kwargs)
            elif message_type == MessageType.CARD:
                return await integration.send_card(**kwargs)
            else:
                return MessageResult(success=False, error_message=f"未知的消息类型: {message_type}")
        except Exception as e:
            logger.error(f"发送消息失败 {name}: {str(e)}")
            return MessageResult(success=False, error_message=str(e))

    async def send_text_to_all(self, content: str):
        """向所有启用的集成发送文本消息"""
        results = {}
        for name, integration in self._integrations.items():
            if integration.is_enabled():
                results[name] = await integration.send_text(content)
        return results

    def enable_integration(self, name: str):
        """启用集成"""
        integration = self._integrations.get(name)
        if integration:
            integration.enable()
            logger.info(f"已启用集成: {name}")

    def disable_integration(self, name: str):
        """禁用集成"""
        integration = self._integrations.get(name)
        if integration:
            integration.disable()
            logger.info(f"已禁用集成: {name}")


# 全局集成管理器实例
integration_manager = IntegrationManager()


def get_integration_manager() -> IntegrationManager:
    """获取集成管理器"""
    return integration_manager


async def send_message(name: str, message_type: str, **kwargs) -> MessageResult:
    """发送消息（对外接口）"""
    try:
        message_type_enum = MessageType[message_type.upper()]
    except KeyError:
        return MessageResult(success=False, error_message=f"未知的消息类型: {message_type}")

    return await integration_manager.send_message(name, message_type_enum, **kwargs)


async def send_text(name: str, content: str, **kwargs) -> MessageResult:
    """发送文本消息（对外接口）"""
    return await integration_manager.send_message(name, MessageType.TEXT, content=content, **kwargs)


async def send_markdown(name: str, content: str, title: Optional[str] = None) -> MessageResult:
    """发送 Markdown 消息（对外接口）"""
    return await integration_manager.send_message(name, MessageType.MARKDOWN, content=content, title=title)


async def send_link(name: str, title: str, text: str, url: str, pic_url: Optional[str] = None) -> MessageResult:
    """发送链接消息（对外接口）"""
    return await integration_manager.send_message(
        name, MessageType.LINK, title=title, text=text, url=url, pic_url=pic_url
    )


def register_integration(
    type: str, name: str, webhook_url: str, enabled: bool = True, secret: Optional[str] = None, **kwargs
):
    """注册集成（对外接口）"""
    try:
        type_enum = IntegrationType[type.upper()]
    except KeyError:
        logger.error(f"未知的集成类型: {type}")
        return

    config = IntegrationConfig(
        type=type_enum, name=name, webhook_url=webhook_url, enabled=enabled, secret=secret, additional_config=kwargs
    )

    integration_manager.register_integration(config)
