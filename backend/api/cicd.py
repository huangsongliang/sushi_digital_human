"""CI/CD API 端点 - 提供自动化测试和部署能力"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.cicd import (
    BoundaryTester,
    HallucinationDetector,
    TestReportGenerator,
)
from backend.cicd.hallucination_detector import HallucinationTestResult
from backend.cicd.test_report import TestResult

router = APIRouter(prefix="/api/cicd", tags=["CI/CD"])

# 全局测试报告生成器实例
report_generator = TestReportGenerator()


class RunTestsRequest(BaseModel):
    """运行测试请求"""
    test_types: Optional[List[str]] = Field(
        default=None,
        description="测试类型列表: hallucination, boundary, all"
    )
    include_trends: bool = Field(default=True, description="是否包含趋势分析")


class DeployRequest(BaseModel):
    """部署请求"""
    version: str = Field(..., min_length=1, max_length=50, description="部署版本")
    environment: str = Field(..., description="部署环境: test, staging, production")
    strategy: str = Field(default="rolling", description="部署策略: rolling, blue_green, canary")
    canary_percentage: float = Field(default=10.0, ge=0, le=100, description="灰度发布百分比")


class HallucinationTestRequest(BaseModel):
    """幻觉检测测试请求"""
    claims: Optional[List[str]] = Field(default=None, description="需要核查的声明列表")
    statements: Optional[List[str]] = Field(default=None, description="需要检测一致性的陈述列表")
    sources: Optional[List[str]] = Field(default=None, description="需要验证的来源列表")


class DeployResponse(BaseModel):
    """部署响应"""
    success: bool = Field(..., description="是否成功")
    deployment_id: str = Field(..., description="部署ID")
    message: str = Field(..., description="部署消息")
    status: str = Field(..., description="部署状态")


@router.post("/run-tests")
async def run_tests(request: RunTestsRequest):
    """运行测试"""
    try:
        test_types = request.test_types or ["all"]
        results: List[TestResult] = []

        if "hallucination" in test_types or "all" in test_types:
            detector = HallucinationDetector()
            hallucination_results = await detector.run_all_tests()
            for r in hallucination_results:
                results.append(TestResult(
                    test_id=r.test_id,
                    test_name=r.test_name,
                    test_type=r.test_type,
                    passed=r.passed,
                    score=r.score,
                    duration_ms=r.duration_ms,
                    timestamp=r.timestamp,
                    details={
                        "fact_check_results": [fr.dict() for fr in r.fact_check_results],
                        "consistency_result": r.consistency_result.dict() if r.consistency_result else None,
                        "source_validation_results": [sr.dict() for sr in r.source_validation_results],
                    },
                ))

        if "boundary" in test_types or "all" in test_types:
            tester = BoundaryTester()
            boundary_results = await tester.run_all_tests()
            for r in boundary_results:
                results.append(TestResult(
                    test_id=r.test_id,
                    test_name=r.test_name,
                    test_type=r.test_type,
                    passed=r.passed,
                    score=r.score,
                    duration_ms=r.duration_ms,
                    timestamp=r.timestamp,
                    details={
                        "extreme_input_results": [er.dict() for er in r.extreme_input_results],
                        "performance_results": [pr.dict() for pr in r.performance_results],
                        "error_handling_results": [er.dict() for er in r.error_handling_results],
                    },
                ))

        report = report_generator.generate_report(results, "CI/CD 测试报告")

        return {
            "success": True,
            "report_id": report.report_id,
            "summary": report.summary.dict(),
            "results": [r.dict() for r in report.results],
            "trends": [t.dict() for t in report.trends] if request.include_trends else None,
            "generated_at": report.generated_at,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-report")
async def get_test_report(
    report_id: Optional[str] = Query(None, description="报告ID"),
    format: str = Query("json", description="输出格式: json, html"),
):
    """获取测试报告"""
    try:
        # 简化实现：返回最新生成的报告
        # 实际应用中应从存储中获取指定的报告
        latest_history = report_generator.get_history(limit=1)
        if not latest_history:
            raise HTTPException(status_code=404, detail="未找到测试报告")

        # 获取最近一次测试的结果来生成报告
        history_results = [
            TestResult(
                test_id=h.test_id,
                test_name=h.test_name,
                test_type=h.test_type,
                passed=h.passed,
                score=h.score,
                duration_ms=0,
                timestamp=h.timestamp,
            )
            for h in latest_history
        ]

        report = report_generator.generate_report(history_results, "CI/CD 测试报告")

        if format.lower() == "html":
            html_content = report_generator.generate_html_report(report)
            return HTMLResponse(content=html_content)
        else:
            return {
                "success": True,
                "report": report.dict(),
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy")
async def deploy(request: DeployRequest):
    """触发部署"""
    try:
        import uuid

        valid_environments = ["test", "staging", "production"]
        if request.environment not in valid_environments:
            raise HTTPException(status_code=400, detail=f"无效的部署环境，必须是: {', '.join(valid_environments)}")

        valid_strategies = ["rolling", "blue_green", "canary"]
        if request.strategy not in valid_strategies:
            raise HTTPException(status_code=400, detail=f"无效的部署策略，必须是: {', '.join(valid_strategies)}")

        # 模拟部署流程
        deployment_id = str(uuid.uuid4())[:8]

        # 根据策略执行不同的部署逻辑
        if request.strategy == "canary" and request.environment == "production":
            message = f"已启动灰度发布策略，版本 {request.version} 将部署到 {request.canary_percentage}% 的流量"
        elif request.strategy == "blue_green":
            message = f"已启动蓝绿部署策略，版本 {request.version} 将部署到绿色环境"
        else:
            message = f"已启动滚动部署策略，版本 {request.version} 将部署到 {request.environment} 环境"

        return {
            "success": True,
            "deployment_id": deployment_id,
            "message": message,
            "status": "deploying",
            "version": request.version,
            "environment": request.environment,
            "strategy": request.strategy,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    test_type: Optional[str] = Query(None, description="按测试类型筛选"),
):
    """获取测试历史记录"""
    try:
        history = report_generator.get_history(limit=limit)

        if test_type:
            history = [h for h in history if h.test_type == test_type]

        return {
            "success": True,
            "count": len(history),
            "history": [h.dict() for h in history],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hallucination/test")
async def hallucination_test(request: HallucinationTestRequest):
    """幻觉检测测试"""
    try:
        detector = HallucinationDetector()
        results: List[HallucinationTestResult] = []

        if request.claims:
            fact_check_results = await detector.fact_check(request.claims)
            results.append(HallucinationTestResult(
                test_id="fact_check_custom",
                test_name="自定义事实核查",
                test_type="fact_check",
                passed=all(r.is_factual for r in fact_check_results),
                fact_check_results=fact_check_results,
                score=sum(r.confidence for r in fact_check_results) / len(fact_check_results) * 100,
                timestamp=0,
                duration_ms=0,
            ))

        if request.statements:
            consistency_result = await detector.consistency_check(request.statements)
            results.append(HallucinationTestResult(
                test_id="consistency_custom",
                test_name="自定义一致性检测",
                test_type="consistency",
                passed=consistency_result.is_consistent,
                consistency_result=consistency_result,
                score=consistency_result.confidence * 100,
                timestamp=0,
                duration_ms=0,
            ))

        if request.sources:
            source_validation_results = await detector.validate_sources(request.sources)
            results.append(HallucinationTestResult(
                test_id="source_validation_custom",
                test_name="自定义来源验证",
                test_type="source_validation",
                passed=all(r.is_valid for r in source_validation_results),
                source_validation_results=source_validation_results,
                score=sum(r.reliability_score for r in source_validation_results) / len(source_validation_results) * 100,
                timestamp=0,
                duration_ms=0,
            ))

        return {
            "success": True,
            "results": [r.dict() for r in results],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
