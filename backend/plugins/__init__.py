"""
插件系统模块
提供完整的插件管理功能，支持：
- 插件基类定义
- 插件加载和注册
- 插件生命周期管理
- 插件配置和依赖管理
"""

import asyncio
import importlib
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class PluginType(Enum):
    """插件类型枚举"""

    RETRIEVER = "retriever"  # 检索插件
    GENERATOR = "generator"  # 生成器插件
    PROCESSOR = "processor"  # 处理器插件
    NOTIFIER = "notifier"  # 通知插件
    AUTH = "auth"  # 认证插件
    STORAGE = "storage"  # 存储插件
    UI = "ui"  # UI 插件
    OTHER = "other"  # 其他类型


class PluginStatus(Enum):
    """插件状态枚举"""

    LOADED = "loaded"  # 已加载
    ACTIVE = "active"  # 活跃中
    INACTIVE = "inactive"  # 非活跃
    ERROR = "error"  # 出错


@dataclass
class PluginInfo:
    """插件信息"""

    name: str
    id: str
    version: str
    description: str
    author: str
    type: PluginType
    status: PluginStatus
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}
        if self.metadata is None:
            self.metadata = {}


class BasePlugin(ABC):
    """插件基类"""

    plugin_info: PluginInfo = None

    def __init__(self):
        self._config = {}
        self._enabled = False

    @abstractmethod
    async def initialize(self, config: Dict[str, Any] = None):
        """初始化插件"""

    @abstractmethod
    async def shutdown(self):
        """关闭插件"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        return True

    def get_info(self) -> PluginInfo:
        """获取插件信息"""
        return self.plugin_info

    def is_enabled(self) -> bool:
        """检查插件是否启用"""
        return self._enabled

    def enable(self):
        """启用插件"""
        self._enabled = True
        if self.plugin_info:
            self.plugin_info.status = PluginStatus.ACTIVE

    def disable(self):
        """禁用插件"""
        self._enabled = False
        if self.plugin_info:
            self.plugin_info.status = PluginStatus.INACTIVE

    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        return self._config

    def set_config(self, config: Dict[str, Any]):
        """设置配置"""
        self._config.update(config)


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._plugin_types: Dict[PluginType, List[str]] = {}
        self._plugins_dir = Path(__file__).parent / "plugins"
        self._enabled_plugins: List[str] = []

    def load_plugins(self, plugins_dir: Optional[str] = None):
        """加载所有插件"""
        if plugins_dir:
            plugins_path = Path(plugins_dir)
        else:
            plugins_path = self._plugins_dir

        if not plugins_path.exists():
            logger.warning(f"插件目录不存在: {plugins_path}")
            return

        # 确保插件目录在 sys.path 中
        if str(plugins_path) not in sys.path:
            sys.path.insert(0, str(plugins_path))

        # 遍历插件目录
        for item in plugins_path.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                self._load_plugin_from_dir(item)

    def _load_plugin_from_dir(self, plugin_dir: Path):
        """从目录加载插件"""
        plugin_name = plugin_dir.name

        try:
            # 尝试导入插件模块
            module_name = f"plugins.{plugin_name}"
            module = importlib.import_module(module_name)

            # 查找插件类
            plugin_class = None
            for name, obj in module.__dict__.items():
                if isinstance(obj, type) and issubclass(obj, BasePlugin) and obj != BasePlugin:
                    plugin_class = obj
                    break

            if plugin_class:
                # 创建插件实例
                plugin = plugin_class()
                self.register_plugin(plugin)
                logger.info(f"已加载插件: {plugin_name}")
            else:
                logger.warning(f"插件 {plugin_name} 未找到插件类")

        except Exception as e:
            logger.error(f"加载插件 {plugin_name} 失败: {str(e)}")

    def register_plugin(self, plugin: BasePlugin):
        """注册插件"""
        if not plugin.plugin_info:
            logger.warning("插件缺少 plugin_info 属性")
            return

        plugin_id = plugin.plugin_info.id
        self._plugins[plugin_id] = plugin

        # 按类型分类
        plugin_type = plugin.plugin_info.type
        if plugin_type not in self._plugin_types:
            self._plugin_types[plugin_type] = []
        if plugin_id not in self._plugin_types[plugin_type]:
            self._plugin_types[plugin_type].append(plugin_id)

    def unregister_plugin(self, plugin_id: str):
        """注销插件"""
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]

            # 从类型分类中移除
            plugin_type = plugin.plugin_info.type
            if plugin_type in self._plugin_types and plugin_id in self._plugin_types[plugin_type]:
                self._plugin_types[plugin_type].remove(plugin_id)

            # 关闭插件
            asyncio.create_task(plugin.shutdown())

            # 删除插件
            del self._plugins[plugin_id]
            logger.info(f"已注销插件: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """获取插件实例"""
        return self._plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[BasePlugin]:
        """按类型获取插件"""
        plugin_ids = self._plugin_types.get(plugin_type, [])
        return [self._plugins.get(pid) for pid in plugin_ids if self._plugins.get(pid)]

    def get_all_plugins(self) -> List[BasePlugin]:
        """获取所有插件"""
        return list(self._plugins.values())

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            return plugin.get_info()
        return None

    def get_all_plugin_info(self) -> List[PluginInfo]:
        """获取所有插件信息"""
        return [plugin.get_info() for plugin in self._plugins.values()]

    async def initialize_plugin(self, plugin_id: str, config: Dict[str, Any] = None):
        """初始化插件"""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            raise ValueError(f"插件不存在: {plugin_id}")

        try:
            await plugin.initialize(config)
            plugin.enable()
            logger.info(f"插件初始化成功: {plugin_id}")
        except Exception as e:
            logger.error(f"插件初始化失败 {plugin_id}: {str(e)}")
            raise

    async def initialize_all_plugins(self, configs: Dict[str, Dict[str, Any]] = None):
        """初始化所有插件"""
        configs = configs or {}

        for plugin_id in self._plugins:
            config = configs.get(plugin_id, {})
            try:
                await self.initialize_plugin(plugin_id, config)
            except Exception as e:
                logger.error(f"初始化插件 {plugin_id} 失败: {str(e)}")

    async def shutdown_plugin(self, plugin_id: str):
        """关闭插件"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            try:
                await plugin.shutdown()
                plugin.disable()
                logger.info(f"插件已关闭: {plugin_id}")
            except Exception as e:
                logger.error(f"关闭插件 {plugin_id} 失败: {str(e)}")

    async def shutdown_all_plugins(self):
        """关闭所有插件"""
        for plugin_id in list(self._plugins.keys()):
            await self.shutdown_plugin(plugin_id)

    async def health_check_all(self) -> Dict[str, bool]:
        """检查所有插件健康状态"""
        results = {}
        for plugin_id, plugin in self._plugins.items():
            try:
                results[plugin_id] = await plugin.health_check()
            except Exception as e:
                logger.error(f"插件健康检查失败 {plugin_id}: {str(e)}")
                results[plugin_id] = False
        return results

    def enable_plugin(self, plugin_id: str):
        """启用插件"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.enable()
            if plugin_id not in self._enabled_plugins:
                self._enabled_plugins.append(plugin_id)

    def disable_plugin(self, plugin_id: str):
        """禁用插件"""
        plugin = self._plugins.get(plugin_id)
        if plugin:
            plugin.disable()
            if plugin_id in self._enabled_plugins:
                self._enabled_plugins.remove(plugin_id)

    def get_enabled_plugins(self) -> List[str]:
        """获取已启用的插件列表"""
        return self._enabled_plugins.copy()


# 全局插件管理器实例
plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """获取插件管理器"""
    return plugin_manager


async def load_and_initialize_plugins():
    """加载并初始化所有插件"""
    plugin_manager.load_plugins()
    await plugin_manager.initialize_all_plugins()


async def shutdown_plugins():
    """关闭所有插件"""
    await plugin_manager.shutdown_all_plugins()
