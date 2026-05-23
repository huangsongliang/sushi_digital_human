"""文档总结 API 路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.summarizer.summary_generator import SummaryGenerator, SummaryType, get_summary_generator
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/summary", tags=["文档总结"])


class SummaryRequest(BaseModel):
    """总结请求"""

    document: str
    summary_type: str = "brief"
    max_length: int = 500


class SummaryResponse(BaseModel):
    """总结响应"""

    summary: str
    summary_type: str
    word_count: int


class KeyPointsRequest(BaseModel):
    """关键要点请求"""

    document: str
    max_points: int = 10


class KeyPointsResponse(BaseModel):
    """关键要点响应"""

    key_points: list
    count: int


class MultiLevelSummaryRequest(BaseModel):
    """多层级总结请求"""

    document: str


class MultiLevelSummaryResponse(BaseModel):
    """多层级总结响应"""

    brief_summary: str
    detailed_summary: str
    key_points: list
    word_count: int
    estimated_read_time: int


class CompareRequest(BaseModel):
    """文档对比请求"""

    document1: str
    document2: str


class CompareResponse(BaseModel):
    """文档对比响应"""

    comparison: str
    doc1_length: int
    doc2_length: int


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(request: SummaryRequest):
    """生成文档总结"""
    try:
        generator = get_summary_generator()

        summary_type = SummaryType(request.summary_type)

        summary = await generator.async_generate_summary(
            document=request.document,
            summary_type=summary_type,
            max_length=request.max_length,
        )

        return SummaryResponse(
            summary=summary,
            summary_type=request.summary_type,
            word_count=len(request.document),
        )

    except Exception as e:
        logger.error(f"生成总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成总结失败: {str(e)}")


@router.post("/key-points", response_model=KeyPointsResponse)
async def extract_key_points(request: KeyPointsRequest):
    """提取关键要点"""
    try:
        generator = get_summary_generator()

        key_points = await generator.async_extract_key_points(
            document=request.document,
            max_points=request.max_points,
        )

        return KeyPointsResponse(
            key_points=key_points,
            count=len(key_points),
        )

    except Exception as e:
        logger.error(f"提取关键要点失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取关键要点失败: {str(e)}")


@router.post("/multi-level", response_model=MultiLevelSummaryResponse)
async def generate_multi_level_summary(request: MultiLevelSummaryRequest):
    """生成多层级总结"""
    try:
        generator = get_summary_generator()

        result = await generator.async_generate_multi_level_summary(
            document=request.document,
        )

        return MultiLevelSummaryResponse(**result)

    except Exception as e:
        logger.error(f"生成多层级总结失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成多层级总结失败: {str(e)}")


@router.post("/compare", response_model=CompareResponse)
async def compare_documents(request: CompareRequest):
    """对比两个文档"""
    try:
        generator = get_summary_generator()

        result = generator.compare_documents(
            document1=request.document1,
            document2=request.document2,
        )

        return CompareResponse(**result)

    except Exception as e:
        logger.error(f"文档对比失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档对比失败: {str(e)}")


@router.post("/timeline")
async def extract_timeline(request: KeyPointsRequest):
    """提取时间线"""
    try:
        generator = get_summary_generator()

        timeline = generator.generate_timeline(document=request.document)

        return {
            "timeline": timeline,
            "count": len(timeline),
        }

    except Exception as e:
        logger.error(f"时间线提取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"时间线提取失败: {str(e)}")


@router.get("/types")
async def get_summary_types():
    """获取支持的总结类型"""
    return {
        "types": [
            {
                "type": "brief",
                "name": "简要总结",
                "description": "简短的文档概要，约200字",
            },
            {
                "type": "detailed",
                "name": "详细总结",
                "description": "详细的文档分析，约1000字",
            },
            {
                "type": "key_points",
                "name": "关键要点",
                "description": "提取文档的核心观点和要点",
            },
            {
                "type": "full",
                "name": "完整总结",
                "description": "包含所有重要信息的完整总结",
            },
        ]
    }
