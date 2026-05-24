"""插件管理 API 路由"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.plugins.plugin_manager import get_plugin_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/plugins", tags=["插件管理"])


class PluginInstallRequest(BaseModel):
    """插件安装请求"""

    name: str = Field(..., description="插件名称")
    config: Dict[str, Any] = Field(default_factory=dict, description="插件配置")


class PluginStatusResponse(BaseModel):
    """插件状态响应"""

    name: str
    version: str
    description: str
    author: str
    enabled: bool


class PluginListResponse(BaseModel):
    """插件列表响应"""

    plugins: List[PluginStatusResponse]
    count: int


@router.get("/list", response_model=PluginListResponse)
async def list_plugins():
    """获取所有插件列表"""
    try:
        manager = get_plugin_manager()
        plugins = manager.list_plugins()
        return PluginListResponse(plugins=plugins, count=len(plugins))
    except Exception as e:
        logger.error(f"获取插件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取插件列表失败: {str(e)}")


@router.get("/{plugin_name}")
async def get_plugin_detail(plugin_name: str):
    """获取插件详情"""
    try:
        manager = get_plugin_manager()
        plugin = manager.get_plugin(plugin_name)
        if not plugin:
            raise HTTPException(status_code=404, detail="插件不存在")

        return {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "author": plugin.author,
            "dependencies": plugin.dependencies,
            "enabled": plugin.name in manager.enabled_plugins,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取插件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取插件详情失败: {str(e)}")


@router.post("/{plugin_name}/enable")
async def enable_plugin(plugin_name: str):
    """启用插件"""
    try:
        manager = get_plugin_manager()
        if manager.enable_plugin(plugin_name):
            return {"status": "success", "message": f"插件 {plugin_name} 已启用"}
        raise HTTPException(status_code=400, detail="插件不存在或已启用")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用插件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"启用插件失败: {str(e)}")


@router.post("/{plugin_name}/disable")
async def disable_plugin(plugin_name: str):
    """禁用插件"""
    try:
        manager = get_plugin_manager()
        if manager.disable_plugin(plugin_name):
            return {"status": "success", "message": f"插件 {plugin_name} 已禁用"}
        raise HTTPException(status_code=400, detail="插件不存在或已禁用")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用插件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"禁用插件失败: {str(e)}")


@router.post("/{plugin_name}/unload")
async def unload_plugin(plugin_name: str):
    """卸载插件"""
    try:
        manager = get_plugin_manager()
        if manager.unload_plugin(plugin_name):
            return {"status": "success", "message": f"插件 {plugin_name} 已卸载"}
        raise HTTPException(status_code=400, detail="插件不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卸载插件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"卸载插件失败: {str(e)}")


@router.post("/discover")
async def discover_plugins():
    """自动发现插件"""
    try:
        manager = get_plugin_manager()
        plugin_dir = manager.plugin_dir or "plugins/"
        discovered = manager.discover_plugins()
        return {
            "discovered_count": len(discovered),
            "plugin_dir": plugin_dir,
            "plugins": [{"name": p.name, "version": p.version, "description": p.description} for p in discovered],
        }
    except Exception as e:
        logger.error(f"发现插件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"发现插件失败: {str(e)}")


@router.get("/hooks/list")
async def list_hooks():
    """获取所有钩子列表"""
    try:
        manager = get_plugin_manager()
        hooks = [{"name": name, "callback_count": len(hook.callbacks)} for name, hook in manager.hooks.items()]
        return {"hooks": hooks, "count": len(hooks)}
    except Exception as e:
        logger.error(f"获取钩子列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取钩子列表失败: {str(e)}")
