"""插件管理器单元测试"""

import pytest
from backend.plugins.plugin_manager import Plugin, Hook, PluginManager


class _TestPlugin(Plugin):
    """测试用插件"""
    name = "test_plugin"
    version = "1.0.0"
    description = "A test plugin"
    author = "test"

    def initialize(self, config: dict) -> bool:
        return True

    def execute(self, *args, **kwargs):
        return {"result": "ok"}

    def shutdown(self):
        pass


class TestPlugin:
    """插件基类测试"""

    def test_plugin_creation(self):
        plugin = _TestPlugin()
        assert plugin.name == "test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.description == "A test plugin"
        assert plugin.author == "test"
        assert plugin.dependencies == []

    def test_plugin_initialize(self):
        plugin = _TestPlugin()
        result = plugin.initialize({})
        assert result is True

    def test_plugin_execute(self):
        plugin = _TestPlugin()
        result = plugin.execute()
        assert result == {"result": "ok"}

    def test_plugin_shutdown(self):
        plugin = _TestPlugin()
        plugin.shutdown()  # no exception


class TestHook:
    """Hook 钩子测试"""

    def test_hook_creation(self):
        hook = Hook("test_hook", priority=5)
        assert hook.name == "test_hook"
        assert hook.priority == 5
        assert hook.callbacks == []

    def test_hook_register(self):
        hook = Hook("test_hook")

        def cb(*args, **kwargs):
            return "hi"

        hook.register(cb)
        assert len(hook.callbacks) == 1

    def test_hook_unregister(self):
        hook = Hook("test_hook")

        def cb(*args, **kwargs):
            return "hi"

        hook.register(cb)
        hook.unregister(cb)
        assert len(hook.callbacks) == 0

    @pytest.mark.asyncio
    async def test_hook_call(self):
        hook = Hook("test_hook")
        results = []

        async def cb(result):
            results.append("called")
            return result

        hook.register(cb)
        output = await hook.call("hello")
        assert len(results) == 1


class TestPluginManager:
    """插件管理器测试"""

    def test_manager_creation(self):
        mgr = PluginManager()
        assert isinstance(mgr.plugins, dict)
        assert isinstance(mgr.hooks, dict)

    def test_register_hook(self):
        mgr = PluginManager()
        hook = mgr.register_hook("my_hook", priority=10)
        assert "my_hook" in mgr.hooks
        assert hook.priority == 10

    @pytest.mark.asyncio
    async def test_trigger_hook_no_callback(self):
        mgr = PluginManager()
        results = await mgr.trigger_hook("nonexistent", data="test")
        assert results == []

    def test_load_plugin(self):
        mgr = PluginManager()
        result = mgr.load_plugin(_TestPlugin, {})
        assert result is True

    def test_get_plugin(self):
        mgr = PluginManager()
        mgr.load_plugin(_TestPlugin, {})
        plugin = mgr.get_plugin("test_plugin")
        assert plugin is not None
        assert plugin.name == "test_plugin"

    def test_list_plugins(self):
        mgr = PluginManager()
        mgr.load_plugin(_TestPlugin, {})
        plugins = mgr.list_plugins()
        assert len(plugins) >= 1
