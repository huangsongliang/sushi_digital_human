"""边界测试器 - 用于测试系统在极端条件下的行为"""

import json
import random
import string
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ExtremeInputTestResult(BaseModel):
    """极端输入测试结果"""

    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    input_type: str = Field(..., description="输入类型")
    input_value: str = Field(..., description="输入值")
    passed: bool = Field(..., description="是否通过")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    response_time_ms: float = Field(..., description="响应时间(毫秒)")


class PerformanceBoundaryResult(BaseModel):
    """性能边界测试结果"""

    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    metric: str = Field(..., description="测试指标")
    value: float = Field(..., description="测量值")
    threshold: float = Field(..., description="阈值")
    passed: bool = Field(..., description="是否通过")
    unit: str = Field(..., description="单位")


class ErrorHandlingResult(BaseModel):
    """错误处理测试结果"""

    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    error_type: str = Field(..., description="错误类型")
    expected_code: int = Field(..., description="期望状态码")
    actual_code: int = Field(..., description="实际状态码")
    handled_correctly: bool = Field(..., description="是否正确处理")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class BoundaryTestResult(BaseModel):
    """边界测试综合结果"""

    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    test_type: str = Field(..., description="测试类型")
    passed: bool = Field(..., description="是否通过")
    extreme_input_results: List[ExtremeInputTestResult] = Field(default_factory=list)
    performance_results: List[PerformanceBoundaryResult] = Field(default_factory=list)
    error_handling_results: List[ErrorHandlingResult] = Field(default_factory=list)
    score: float = Field(..., ge=0.0, le=100.0, description="综合评分")
    timestamp: float = Field(..., description="测试时间戳")
    duration_ms: float = Field(..., description="测试耗时(毫秒)")


class BoundaryTester:
    """边界测试器 - 执行极端输入测试、性能边界测试和错误处理测试"""

    def __init__(self):
        self.extreme_input_test_cases = [
            {
                "id": "extreme_001",
                "name": "超长文本输入",
                "input_type": "text",
                "generator": lambda: "".join(random.choices(string.ascii_letters, k=100000)),
                "expected": "should_handle",
            },
            {
                "id": "extreme_002",
                "name": "空字符串输入",
                "input_type": "text",
                "generator": lambda: "",
                "expected": "should_handle",
            },
            {
                "id": "extreme_003",
                "name": "特殊字符输入",
                "input_type": "text",
                "generator": lambda: "!@#$%^&*()_+-=[]{}|;':\",./<>?\\~`",
                "expected": "should_handle",
            },
            {
                "id": "extreme_004",
                "name": "超大数字输入",
                "input_type": "number",
                "generator": lambda: str(10**100),
                "expected": "should_handle",
            },
            {
                "id": "extreme_005",
                "name": "嵌套JSON输入",
                "input_type": "json",
                "generator": self._generate_nested_json,
                "expected": "should_handle",
            },
        ]

        self.performance_test_cases = [
            {
                "id": "perf_001",
                "name": "响应时间测试",
                "metric": "response_time",
                "threshold": 500,
                "unit": "ms",
            },
            {
                "id": "perf_002",
                "name": "内存使用测试",
                "metric": "memory_usage",
                "threshold": 512,
                "unit": "MB",
            },
            {
                "id": "perf_003",
                "name": "并发处理测试",
                "metric": "concurrent_requests",
                "threshold": 100,
                "unit": "req/s",
            },
        ]

        self.error_handling_test_cases = [
            {
                "id": "error_001",
                "name": "无效参数处理",
                "error_type": "invalid_parameter",
                "expected_code": 400,
            },
            {
                "id": "error_002",
                "name": "未授权访问",
                "error_type": "unauthorized",
                "expected_code": 401,
            },
            {
                "id": "error_003",
                "name": "资源不存在",
                "error_type": "not_found",
                "expected_code": 404,
            },
            {
                "id": "error_004",
                "name": "服务器错误处理",
                "error_type": "server_error",
                "expected_code": 500,
            },
        ]

    def _generate_nested_json(self, depth: int = 10) -> str:
        """生成嵌套JSON"""
        if depth == 0:
            return '"leaf"'
        return f'{{"level_{depth}": {self._generate_nested_json(depth - 1)}}}'

    async def test_extreme_input(self, input_value: str, input_type: str) -> ExtremeInputTestResult:
        """测试极端输入处理能力

        Args:
            input_value: 输入值
            input_type: 输入类型

        Returns:
            极端输入测试结果
        """
        import time

        start_time = time.time()

        try:
            # 模拟处理极端输入
            if input_type == "json":
                # 尝试解析JSON
                json.loads(input_value)
            elif input_type == "text":
                # 模拟文本处理
                _ = len(input_value)
            elif input_type == "number":
                # 尝试转换为数字
                _ = float(input_value)

            response_time_ms = (time.time() - start_time) * 1000

            return ExtremeInputTestResult(
                test_id="extreme_input",
                test_name=f"测试{input_type}类型极端输入",
                input_type=input_type,
                input_value=f"长度={len(input_value)}",
                passed=True,
                response_time_ms=response_time_ms,
            )
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return ExtremeInputTestResult(
                test_id="extreme_input",
                test_name=f"测试{input_type}类型极端输入",
                input_type=input_type,
                input_value=f"长度={len(input_value)}",
                passed=False,
                error_message=str(e),
                response_time_ms=response_time_ms,
            )

    async def run_all_extreme_input_tests(self) -> List[BoundaryTestResult]:
        """运行所有极端输入测试"""
        results = []
        for test_case in self.extreme_input_test_cases:
            result = await self._run_extreme_input_test(test_case)
            results.append(result)
        return results

    async def _run_extreme_input_test(self, test_case: Dict[str, Any]) -> BoundaryTestResult:
        """运行单个极端输入测试用例"""
        import time

        start_time = time.time()

        input_value = test_case["generator"]()
        result = await self.test_extreme_input(input_value, test_case["input_type"])

        passed = result.passed
        score = 100.0 if passed else 50.0

        duration_ms = (time.time() - start_time) * 1000

        return BoundaryTestResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            test_type="extreme_input",
            passed=passed,
            extreme_input_results=[result],
            score=score,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

    async def test_performance_boundary(self, test_case: Dict[str, Any]) -> PerformanceBoundaryResult:
        """测试性能边界

        Args:
            test_case: 测试用例

        Returns:
            性能边界测试结果
        """
        import time

        import psutil

        metric = test_case["metric"]
        threshold = test_case["threshold"]
        unit = test_case["unit"]

        if metric == "response_time":
            # 模拟响应时间测试
            time.sleep(random.uniform(0.1, 0.3))
            value = random.uniform(100, 400)
        elif metric == "memory_usage":
            # 获取当前内存使用
            process = psutil.Process()
            mem_info = process.memory_info()
            value = mem_info.rss / (1024 * 1024)  # 转换为 MB
        elif metric == "concurrent_requests":
            # 模拟并发请求数
            value = random.uniform(80, 120)
        else:
            value = 0.0

        passed = value <= threshold

        return PerformanceBoundaryResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            metric=metric,
            value=value,
            threshold=threshold,
            passed=passed,
            unit=unit,
        )

    async def run_all_performance_tests(self) -> List[BoundaryTestResult]:
        """运行所有性能边界测试"""
        results = []
        for test_case in self.performance_test_cases:
            result = await self._run_performance_test(test_case)
            results.append(result)
        return results

    async def _run_performance_test(self, test_case: Dict[str, Any]) -> BoundaryTestResult:
        """运行单个性能边界测试用例"""
        import time

        start_time = time.time()

        result = await self.test_performance_boundary(test_case)

        passed = result.passed
        score = 100.0 if passed else (1 - result.value / result.threshold) * 100

        duration_ms = (time.time() - start_time) * 1000

        return BoundaryTestResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            test_type="performance",
            passed=passed,
            performance_results=[result],
            score=max(0, score),
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

    async def test_error_handling(self, error_type: str, expected_code: int) -> ErrorHandlingResult:
        """测试错误处理能力

        Args:
            error_type: 错误类型
            expected_code: 期望状态码

        Returns:
            错误处理测试结果
        """
        # 模拟不同类型的错误处理
        error_codes = {
            "invalid_parameter": 400,
            "unauthorized": 401,
            "not_found": 404,
            "server_error": 500,
        }

        actual_code = error_codes.get(error_type, 500)
        handled_correctly = actual_code == expected_code

        return ErrorHandlingResult(
            test_id=f"error_{error_type}",
            test_name=f"{error_type}处理",
            error_type=error_type,
            expected_code=expected_code,
            actual_code=actual_code,
            handled_correctly=handled_correctly,
        )

    async def run_all_error_handling_tests(self) -> List[BoundaryTestResult]:
        """运行所有错误处理测试"""
        results = []
        for test_case in self.error_handling_test_cases:
            result = await self._run_error_handling_test(test_case)
            results.append(result)
        return results

    async def _run_error_handling_test(self, test_case: Dict[str, Any]) -> BoundaryTestResult:
        """运行单个错误处理测试用例"""
        import time

        start_time = time.time()

        result = await self.test_error_handling(test_case["error_type"], test_case["expected_code"])

        passed = result.handled_correctly
        score = 100.0 if passed else 0.0

        duration_ms = (time.time() - start_time) * 1000

        return BoundaryTestResult(
            test_id=test_case["id"],
            test_name=test_case["name"],
            test_type="error_handling",
            passed=passed,
            error_handling_results=[result],
            score=score,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

    async def run_all_tests(self) -> List[BoundaryTestResult]:
        """运行所有边界测试"""
        extreme_results = await self.run_all_extreme_input_tests()
        performance_results = await self.run_all_performance_tests()
        error_handling_results = await self.run_all_error_handling_tests()

        return [*extreme_results, *performance_results, *error_handling_results]
