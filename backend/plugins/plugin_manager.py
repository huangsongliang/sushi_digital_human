"""插件系统架构
支持自定义插件扩展和钩子机制
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class Plugin(ABC):
    """插件基类"""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = []

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""

    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """执行插件功能"""

    def shutdown(self):
        """关闭插件"""


class Hook:
    """钩子定义"""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
        self.callbacks: List[Callable] = []

    def register(self, callback: Callable):
        """注册回调函数"""
        self.callbacks.append(callback)
        self.callbacks.sort(key=lambda x: self.priority, reverse=True)

    def unregister(self, callback: Callable):
        """取消注册回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def call(self, *args, **kwargs) -> List[Any]:
        """调用所有回调"""
        results = []
        for callback in self.callbacks:
            try:
                result = callback(*args, **kwargs)
                if inspect.iscoroutine(result):
                    result = await result
                results.append(result)
            except Exception as e:
                logger.error(f"钩子执行失败: {self.name}, error={str(e)}")
        return results


class PluginManager:
    """插件管理器"""

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, Hook] = {}
        self.plugin_dir = plugin_dir
        self.enabled_plugins: List[str] = []

    def register_hook(self, name: str, priority: int = 0) -> Hook:
        """注册钩子"""
        if name not in self.hooks:
            self.hooks[name] = Hook(name, priority)
        return self.hooks[name]

    def add_hook_callback(self, hook_name: str, callback: Callable, priority: int = 0):
        """添加钩子回调"""
        if hook_name not in self.hooks:
            self.register_hook(hook_name, priority)
        self.hooks[hook_name].register(callback)

    async def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """触发钩子"""
        if hook_name in self.hooks:
            return await self.hooks[hook_name].call(*args, **kwargs)
        return []

    def load_plugin(self, plugin_class: Type[Plugin], config: Dict[str, Any]) -> bool:
        """加载插件"""
        try:
            plugin_name = plugin_class.name

            if plugin_name in self.plugins:
                logger.warning(f"插件已存在: {plugin_name}")
                return False

            plugin = plugin_class()
            if plugin.initialize(config):
                self.plugins[plugin_name] = plugin
                self.enabled_plugins.append(plugin_name)
                logger.info(f"插件加载成功: {plugin_name} v{plugin.version}")
                return True
            else:
                logger.error(f"插件初始化失败: {plugin_name}")
                return False

        except Exception as e:
            logger.error(f"加载插件失败: {str(e)}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        if plugin_name in self.plugins:
            try:
                plugin = self.plugins[plugin_name]
                plugin.shutdown()
                del self.plugins[plugin_name]
                if plugin_name in self.enabled_plugins:
                    self.enabled_plugins.remove(plugin_name)
                logger.info(f"插件卸载成功: {plugin_name}")
                return True
            except Exception as e:
                logger.error(f"卸载插件失败: {plugin_name}: {str(e)}")
                return False
        return False

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self.plugins.get(plugin_name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """列出所有插件"""
        return [
            {
                "name": plugin.name,
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "enabled": plugin.name in self.enabled_plugins,
            }
            for plugin in self.plugins.values()
        ]

    def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        if plugin_name in self.plugins and plugin_name not in self.enabled_plugins:
            self.enabled_plugins.append(plugin_name)
            logger.info(f"插件已启用: {plugin_name}")
            return True
        return False

    def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        if plugin_name in self.enabled_plugins:
            self.enabled_plugins.remove(plugin_name)
            logger.info(f"插件已禁用: {plugin_name}")
            return True
        return False

    def discover_plugins(self) -> List[Type[Plugin]]:
        """自动发现插件"""
        discovered = []

        if not self.plugin_dir:
            return discovered

        plugin_path = Path(self.plugin_dir)
        if not plugin_path.exists():
            return discovered

        for file_path in plugin_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            try:
                module_name = f"plugins.{file_path.stem}"
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin and hasattr(obj, "name"):
                        discovered.append(obj)

            except Exception as e:
                logger.error(f"发现插件失败 {file_path}: {str(e)}")

        logger.info(f"发现 {len(discovered)} 个插件")
        return discovered


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """获取插件管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        logger.info("插件管理器已初始化")
    return _plugin_manager


class DocumentProcessorPlugin(Plugin):
    """文档处理插件示例"""

    name = "document_processor"
    version = "1.0.0"
    description = "文档处理扩展插件"
    author = "System"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        return True

    def execute(self, text: str) -> str:
        return f"[Processed by {self.name}] {text}"


class AIModelPlugin(Plugin):
    """AI 模型插件示例"""

    name = "ai_model"
    version = "1.0.0"
    description = "AI 模型扩展插件"
    author = "System"

    def initialize(self, config: Dict[str, Any]) -> bool:
        self.config = config
        return True

    def execute(self, prompt: str) -> str:
        return f"[AI Response for: {prompt}]"
