"""总结 API 路由"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.chain.summary_chain import (
    SummaryType,
    extract_key_points,
    generate_title,
    summarize_conversation,
    summarize_documents,
    summarize_text,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/summary", tags=["总结"])


class TextSummaryRequest(BaseModel):
    content: str
    type: str = "brief"


class DocumentsSummaryRequest(BaseModel):
    documents: List[dict]
    type: str = "detailed"


class ConversationSummaryRequest(BaseModel):
    messages: List[dict]
    type: str = "brief"


class KeyPointsRequest(BaseModel):
    content: str
    max_points: int = 10


class TitleRequest(BaseModel):
    content: str
    max_length: int = 50


@router.post("/text")
async def summarize_text_endpoint(request: TextSummaryRequest):
    """总结文本内容"""
    try:
        result = await summarize_text(request.content, request.type)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"文本总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents")
async def summarize_documents_endpoint(request: DocumentsSummaryRequest):
    """总结多个文档"""
    try:
        result = await summarize_documents(request.documents, request.type)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"文档总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversation")
async def summarize_conversation_endpoint(request: ConversationSummaryRequest):
    """总结对话历史"""
    try:
        result = await summarize_conversation(request.messages)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"对话总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/key-points")
async def extract_key_points_endpoint(request: KeyPointsRequest):
    """提取关键要点"""
    try:
        points = await extract_key_points(request.content, request.max_points)
        return {"status": "success", "data": {"points": points}}
    except Exception as e:
        logger.error(f"提取关键要点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/title")
async def generate_title_endpoint(request: TitleRequest):
    """生成标题"""
    try:
        title = await generate_title(request.content, request.max_length)
        return {"status": "success", "data": {"title": title}}
    except Exception as e:
        logger.error(f"生成标题失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
