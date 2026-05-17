"""
Dify 集成 API 接口
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from backend.core.dify import (
    DifyIntegration,
    DifyToolCall,
    get_dify_integration,
    get_webhook_handler
)


router = APIRouter(prefix="/api/dify", tags=["Dify 集成"])


class ToolCallRequest(BaseModel):
    """工具调用请求（符合 Dify 工具调用规范）"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(..., description="工具参数")
    task_id: str = Field(..., description="Dify 任务 ID")


class WebhookRequest(BaseModel):
    """Webhook 请求"""
    event_type: str = Field(..., description="事件类型")
    payload: Dict[str, Any] = Field(..., description="事件数据")


@router.post("/tool/execute")
async def execute_tool(request: ToolCallRequest):
    """
    执行 Dify 工具调用
    
    这是 Dify 工作流中调用我们 RAG 工具的入口
    """
    try:
        dify = get_dify_integration()
        
        tool_call = DifyToolCall(
            tool_name=request.tool_name,
            arguments=request.arguments,
            task_id=request.task_id
        )
        
        result = dify.execute_tool(tool_call)
        response = dify.generate_tool_response(request.task_id, result)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tool/definition")
async def get_tool_definition():
    """
    获取工具定义
    
    返回符合 Dify 工具规范的工具定义，用于在 Dify 平台注册
    """
    dify = get_dify_integration()
    tool = dify.get_rag_search_tool()
    
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters,
        "tool_type": tool.tool_type
    }


@router.post("/webhook")
async def handle_webhook(request: WebhookRequest):
    """
    处理 Dify Webhook 事件
    
    支持的事件类型:
    - message_created: 消息创建
    - message_updated: 消息更新
    - tool_called: 工具调用
    """
    handler = get_webhook_handler()
    result = handler.handle_webhook(request.event_type, request.payload)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.post("/configure")
async def configure_dify(
    api_key: str,
    base_url: Optional[str] = "https://api.dify.ai/v1"
):
    """
    配置 Dify API
    
    Args:
        api_key: Dify API Key
        base_url: Dify API 基础地址
    """
    dify = get_dify_integration()
    dify.configure(api_key, base_url)
    
    return {"success": True, "message": "Dify 配置成功"}


@router.get("/applications")
async def list_applications(
    x_dify_api_key: Optional[str] = Header(None)
):
    """
    获取 Dify 应用列表
    
    需要在请求头中提供 Dify API Key
    """
    dify = get_dify_integration()
    
    if x_dify_api_key:
        dify.configure(x_dify_api_key)
    
    result = dify.list_applications()
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.post("/applications")
async def create_application(
    name: str,
    description: Optional[str] = "",
    x_dify_api_key: Optional[str] = Header(None)
):
    """
    在 Dify 中创建应用
    
    需要在请求头中提供 Dify API Key
    """
    dify = get_dify_integration()
    
    if x_dify_api_key:
        dify.configure(x_dify_api_key)
    
    result = dify.create_application(name, description)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"success": True, "data": result}


@router.get("/applications/{app_id}")
async def get_application(
    app_id: str,
    x_dify_api_key: Optional[str] = Header(None)
):
    """
    获取 Dify 应用详情
    
    需要在请求头中提供 Dify API Key
    """
    dify = get_dify_integration()
    
    if x_dify_api_key:
        dify.configure(x_dify_api_key)
    
    result = dify.get_application(app_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@router.delete("/applications/{app_id}")
async def delete_application(
    app_id: str,
    x_dify_api_key: Optional[str] = Header(None)
):
    """
    删除 Dify 应用
    
    需要在请求头中提供 Dify API Key
    """
    dify = get_dify_integration()
    
    if x_dify_api_key:
        dify.configure(x_dify_api_key)
    
    result = dify.delete_application(app_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"success": True, "message": "应用删除成功"}


@router.post("/chat")
async def chat_with_dify(
    app_id: str,
    message: str,
    user_id: Optional[str] = "default",
    x_dify_api_key: Optional[str] = Header(None)
):
    """
    通过 Dify 进行聊天
    
    需要在请求头中提供 Dify API Key
    """
    dify = get_dify_integration()
    
    if x_dify_api_key:
        dify.configure(x_dify_api_key)
    
    result = dify.chat_completion(app_id, message, user_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


# ==================== Dify 工作流集成说明 ====================
# 
# 在 Dify 中使用此工具的步骤：
# 
# 1. 在 Dify 平台创建一个应用
# 2. 进入工作流编辑器
# 3. 添加一个"HTTP 请求"节点
# 4. 配置请求：
#    - 方法：POST
#    - URL: http://your-server/api/dify/tool/execute
#    - 内容类型：application/json
#    - 请求体：
#      {
#        "tool_name": "search_sushi_documents",
#        "arguments": {
#          "query": "{{inputs.query}}",
#          "top_k": 3
#        },
#        "task_id": "{{workflow.task_id}}"
#      }
# 5. 将返回结果连接到后续节点（如"总结回答"节点）
# 
# 或者使用 Dify 的"自定义工具"功能：
# 1. 在应用设置中添加自定义工具
# 2. 使用 GET /api/dify/tool/definition 获取工具定义
# 3. 将定义粘贴到 Dify 的自定义工具配置中
# 4. Dify 会自动生成工具调用代码
