"""Agent API 端点"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from backend.agent import get_agent_manager
from backend.core.auth_manager import get_auth_manager
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])


class AgentRequest(BaseModel):
    """Agent请求模型"""

    query: str
    session_id: Optional[str] = None


class AgentResponse(BaseModel):
    """Agent响应模型"""

    answer: str
    sources: List[Dict[str, Any]] = []
    thought: Optional[str] = None
    tool_used: Optional[str] = None


class ToolInfo(BaseModel):
    """工具信息模型"""

    name: str
    description: str


@router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest):
    """Agent对话接口（支持多轮对话）"""
    try:
        agent_manager = get_agent_manager()
        result = await agent_manager.run(query=request.query, session_id=request.session_id)

        return AgentResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            thought=result.get("thought"),
            tool_used=result.get("tool_used"),
        )

    except Exception as e:
        logger.error(f"Agent API错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=List[ToolInfo])
async def list_tools():
    """获取可用工具列表"""
    try:
        agent_manager = get_agent_manager()
        tools = []
        for tool in agent_manager.tools:
            tools.append(ToolInfo(name=tool.name, description=tool.description))
        return tools

    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def agent_health():
    """Agent健康检查"""
    try:
        agent_manager = get_agent_manager()
        return {"status": "healthy", "tools_count": len(agent_manager.tools)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent服务异常: {str(e)}")
