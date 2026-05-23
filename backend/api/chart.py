"""图表内容解析 API 路由"""

import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.data_loader.chart_parser import ChartClassifier, ChartDescriber, ChartDetector, ChartType, DataExtractor
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chart", tags=["图表解析"])


class ChartAnalyzeRequest(BaseModel):
    """图表分析请求"""

    chart_type: Optional[str] = Field(default=None, description="图表类型（可选）")
    extract_data: bool = Field(default=True, description="是否提取数据")
    generate_description: bool = Field(default=True, description="是否生成描述")


class ChartAnalyzeResponse(BaseModel):
    """图表分析响应"""

    status: str
    detected: bool
    chart_type: Optional[str] = None
    confidence: float
    data: Optional[dict] = None
    description: Optional[str] = None
    message: str


class ChartExtractRequest(BaseModel):
    """图表数据提取请求"""

    chart_type: str = Field(..., description="图表类型：bar/line/pie/flowchart")


class ChartExtractResponse(BaseModel):
    """图表数据提取响应"""

    status: str
    chart_type: str
    data: dict
    message: str


class ChartQueryRequest(BaseModel):
    """图表问答请求"""

    question: str = Field(..., min_length=1, max_length=500, description="用户问题")


class ChartQueryResponse(BaseModel):
    """图表问答响应"""

    status: str
    question: str
    answer: str
    message: str


class ChartTypesResponse(BaseModel):
    """支持的图表类型响应"""

    types: List[dict]
    total: int


@router.post("/analyze", response_model=ChartAnalyzeResponse)
async def analyze_chart_endpoint(
    file: UploadFile = File(...),
    extract_data: bool = True,
    generate_description: bool = True,
):
    """
    分析图表 - 检测类型、提取数据、生成描述

    Args:
        file: 图表图像文件
        extract_data: 是否提取数据
        generate_description: 是否生成描述

    Returns:
        ChartAnalyzeResponse: 分析结果
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file_ext}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            detector = ChartDetector()
            detection_result = detector.detect(tmp_file_path)

            result = {
                "status": "success",
                "detected": detection_result.detected,
                "chart_type": detection_result.chart_type.value if detection_result.detected else None,
                "confidence": detection_result.confidence,
                "data": None,
                "description": None,
                "message": "图表分析完成",
            }

            if extract_data and detection_result.detected:
                extractor = DataExtractor()
                result["data"] = extractor.extract(tmp_file_path, detection_result.chart_type)

            if generate_description and detection_result.detected:
                describer = ChartDescriber()
                result["description"] = await describer.describe(
                    tmp_file_path, detection_result.chart_type, result.get("data")
                )

            return ChartAnalyzeResponse(**result)

        finally:
            if Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图表分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表分析失败: {str(e)}")


@router.post("/extract", response_model=ChartExtractResponse)
async def extract_chart_data(
    file: UploadFile = File(...),
    chart_type: str = "bar",
):
    """
    提取图表数据

    Args:
        file: 图表图像文件
        chart_type: 图表类型（bar/line/pie/flowchart）

    Returns:
        ChartExtractResponse: 提取的数据
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        try:
            chart_type_enum = ChartType(chart_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的图表类型: {chart_type}，支持的类型: bar/line/pie/flowchart",
            )

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file_ext}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            extractor = DataExtractor()
            data = extractor.extract(tmp_file_path, chart_type_enum)

            if data.get("status") == "error":
                return ChartExtractResponse(
                    status="error",
                    chart_type=chart_type,
                    data={},
                    message=data.get("message", "数据提取失败"),
                )

            return ChartExtractResponse(
                status="success",
                chart_type=chart_type,
                data=data,
                message="数据提取成功",
            )

        finally:
            if Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图表数据提取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表数据提取失败: {str(e)}")


@router.post("/query", response_model=ChartQueryResponse)
async def query_chart(
    file: UploadFile = File(...),
    question: str = "这张图表展示的主要内容是什么？",
    chart_type: Optional[str] = None,
):
    """
    图表问答 - 对图表内容进行问答

    Args:
        file: 图表图像文件
        question: 用户问题
        chart_type: 图表类型（可选）

    Returns:
        ChartQueryResponse: 问答结果
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        if not question or len(question.strip()) == 0:
            raise HTTPException(status_code=400, detail="问题不能为空")

        if len(question) > 500:
            raise HTTPException(status_code=400, detail="问题长度不能超过 500 字符")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file_ext}")

        chart_type_enum = None
        if chart_type:
            try:
                chart_type_enum = ChartType(chart_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的图表类型: {chart_type}",
                )

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            describer = ChartDescriber()
            answer = await describer.query(tmp_file_path, question.strip(), chart_type_enum)

            return ChartQueryResponse(
                status="success",
                question=question.strip(),
                answer=answer,
                message="问答完成",
            )

        finally:
            if Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图表问答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表问答失败: {str(e)}")


@router.get("/types", response_model=ChartTypesResponse)
async def get_supported_chart_types():
    """
    获取支持的图表类型列表

    Returns:
        ChartTypesResponse: 支持的图表类型
    """
    classifier = ChartClassifier()
    supported_types = classifier.get_supported_types()

    type_info = {
        "bar": {"name": "柱状图", "description": "使用垂直或水平条形展示数据比较"},
        "line": {"name": "折线图", "description": "使用线条展示数据趋势和变化"},
        "pie": {"name": "饼图", "description": "使用圆形切片展示数据占比"},
        "flowchart": {"name": "流程图", "description": "展示流程和步骤关系"},
        "table": {"name": "表格", "description": "行列式数据结构"},
        "mixed": {"name": "混合图表", "description": "多种图表类型的组合"},
    }

    types_list = []
    for type_key in supported_types:
        info = type_info.get(type_key, {"name": type_key, "description": "未知类型"})
        types_list.append({"type": type_key, **info})

    return ChartTypesResponse(
        types=types_list,
        total=len(types_list),
    )


@router.post("/detect")
async def detect_chart_type(
    file: UploadFile = File(...),
):
    """
    检测图表类型

    Args:
        file: 图表图像文件

    Returns:
        dict: 检测结果
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file_ext}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            detector = ChartDetector()
            result = detector.detect(tmp_file_path)

            return {
                "status": "success",
                "detected": result.detected,
                "chart_type": result.chart_type.value if result.detected else None,
                "confidence": result.confidence,
                "bounding_boxes": result.bounding_boxes,
                "message": "图表检测完成" if result.detected else "未检测到图表",
            }

        finally:
            if Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图表检测失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表检测失败: {str(e)}")


@router.post("/describe")
async def describe_chart(
    file: UploadFile = File(...),
    chart_type: Optional[str] = None,
):
    """
    生成图表描述

    Args:
        file: 图表图像文件
        chart_type: 图表类型（可选）

    Returns:
        dict: 图表描述
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        chart_type_enum = None
        if chart_type:
            try:
                chart_type_enum = ChartType(chart_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的图表类型: {chart_type}",
                )

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"]:
            raise HTTPException(status_code=400, detail=f"不支持的图片格式: {file_ext}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            describer = ChartDescriber()
            description = await describer.describe(tmp_file_path, chart_type_enum)

            return {
                "status": "success",
                "description": description,
                "chart_type": chart_type_enum.value if chart_type_enum else "auto-detected",
                "message": "描述生成成功",
            }

        finally:
            if Path(tmp_file_path).exists():
                Path(tmp_file_path).unlink()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图表描述生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表描述生成失败: {str(e)}")
