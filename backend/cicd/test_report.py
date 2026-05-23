"""测试报告生成器 - 生成测试结果统计和趋势分析"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TestResult(BaseModel):
    """单个测试结果"""

    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    test_type: str = Field(..., description="测试类型")
    passed: bool = Field(..., description="是否通过")
    score: float = Field(..., ge=0.0, le=100.0, description="测试得分")
    duration_ms: float = Field(..., description="测试耗时(毫秒)")
    timestamp: float = Field(..., description="测试时间戳")
    details: Optional[Dict[str, Any]] = Field(default=None, description="详细信息")


class TestSummary(BaseModel):
    """测试摘要"""

    total_tests: int = Field(..., description="总测试数")
    passed_tests: int = Field(..., description="通过测试数")
    failed_tests: int = Field(..., description="失败测试数")
    pass_rate: float = Field(..., ge=0.0, le=100.0, description="通过率")
    average_score: float = Field(..., ge=0.0, le=100.0, description="平均分")
    total_duration_ms: float = Field(..., description="总耗时(毫秒)")
    average_duration_ms: float = Field(..., description="平均耗时(毫秒)")


class TrendData(BaseModel):
    """趋势数据点"""

    timestamp: float = Field(..., description="时间戳")
    pass_rate: float = Field(..., ge=0.0, le=100.0, description="通过率")
    average_score: float = Field(..., ge=0.0, le=100.0, description="平均分")
    total_tests: int = Field(..., description="测试数")


class TestReport(BaseModel):
    """测试报告"""

    report_id: str = Field(..., description="报告ID")
    report_name: str = Field(..., description="报告名称")
    generated_at: float = Field(..., description="生成时间戳")
    summary: TestSummary = Field(..., description="测试摘要")
    results: List[TestResult] = Field(default_factory=list, description="测试结果列表")
    trends: Optional[List[TrendData]] = Field(default=None, description="趋势数据")


class TestHistory(BaseModel):
    """测试历史记录"""

    history_id: str = Field(..., description="历史记录ID")
    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    test_type: str = Field(..., description="测试类型")
    passed: bool = Field(..., description="是否通过")
    score: float = Field(..., ge=0.0, le=100.0, description="测试得分")
    timestamp: float = Field(..., description="测试时间戳")
    environment: str = Field(..., description="测试环境")
    version: str = Field(..., description="版本号")


class TestReportGenerator:
    """测试报告生成器 - 生成统计报告和趋势分析"""

    def __init__(self):
        self.history_store: List[TestHistory] = []

    def calculate_summary(self, results: List[TestResult]) -> TestSummary:
        """计算测试摘要统计

        Args:
            results: 测试结果列表

        Returns:
            测试摘要
        """
        if not results:
            return TestSummary(
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                pass_rate=0.0,
                average_score=0.0,
                total_duration_ms=0.0,
                average_duration_ms=0.0,
            )

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        pass_rate = (passed / total) * 100
        average_score = sum(r.score for r in results) / total
        total_duration = sum(r.duration_ms for r in results)
        average_duration = total_duration / total

        return TestSummary(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=round(pass_rate, 2),
            average_score=round(average_score, 2),
            total_duration_ms=round(total_duration, 2),
            average_duration_ms=round(average_duration, 2),
        )

    def generate_report(self, results: List[TestResult], report_name: str = "测试报告") -> TestReport:
        """生成测试报告

        Args:
            results: 测试结果列表
            report_name: 报告名称

        Returns:
            测试报告
        """
        summary = self.calculate_summary(results)
        trends = self.calculate_trends(results)

        report = TestReport(
            report_id=self._generate_id(),
            report_name=report_name,
            generated_at=datetime.now().timestamp(),
            summary=summary,
            results=results,
            trends=trends,
        )

        # 保存到历史记录
        for result in results:
            self._add_to_history(result)

        return report

    def _generate_id(self) -> str:
        """生成唯一ID"""
        import uuid

        return str(uuid.uuid4())[:8]

    def _add_to_history(self, result: TestResult):
        """添加到历史记录"""
        history = TestHistory(
            history_id=self._generate_id(),
            test_id=result.test_id,
            test_name=result.test_name,
            test_type=result.test_type,
            passed=result.passed,
            score=result.score,
            timestamp=result.timestamp,
            environment="test",
            version="1.0.0",
        )
        self.history_store.append(history)

    def calculate_trends(self, current_results: List[TestResult]) -> List[TrendData]:
        """计算趋势数据

        Args:
            current_results: 当前测试结果

        Returns:
            趋势数据列表
        """
        trends = []

        # 添加当前结果
        current_summary = self.calculate_summary(current_results)
        trends.append(
            TrendData(
                timestamp=datetime.now().timestamp(),
                pass_rate=current_summary.pass_rate,
                average_score=current_summary.average_score,
                total_tests=current_summary.total_tests,
            )
        )

        # 模拟历史趋势数据
        import random

        for i in range(6):
            timestamp = datetime.now().timestamp() - (i + 1) * 3600  # 每小时一个数据点
            pass_rate = 70 + random.uniform(-10, 20)
            average_score = 75 + random.uniform(-15, 15)

            trends.append(
                TrendData(
                    timestamp=timestamp,
                    pass_rate=round(min(100, max(0, pass_rate)), 2),
                    average_score=round(min(100, max(0, average_score)), 2),
                    total_tests=len(current_results),
                )
            )

        return sorted(trends, key=lambda x: x.timestamp)

    def generate_json_report(self, report: TestReport) -> str:
        """生成JSON格式报告

        Args:
            report: 测试报告

        Returns:
            JSON字符串
        """
        return json.dumps(report.dict(), ensure_ascii=False, indent=2)

    def generate_html_report(self, report: TestReport) -> str:
        """生成HTML格式报告

        Args:
            report: 测试报告

        Returns:
            HTML字符串
        """
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.report_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px; background: #f5f5f5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px; margin-bottom: 20px;
        }}
        .summary-card {{
            background: white; padding: 20px;
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-card .label {{ color: #666; font-size: 14px; margin-bottom: 8px; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; }}
        .summary-card.pass {{ color: #10b981; }}
        .summary-card.fail {{ color: #ef4444; }}
        .summary-card.info {{ color: #3b82f6; }}
        .test-list {{ background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }}
        .test-list table {{ width: 100%; border-collapse: collapse; }}
        .test-list th, .test-list td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid #eee; }}
        .test-list th {{ background: #f8f9fa; font-weight: 600; color: #333; }}
        .test-list tr:hover {{ background: #f8f9fa; }}
        .status-pass {{ color: #10b981; font-weight: 600; }}
        .status-fail {{ color: #ef4444; font-weight: 600; }}
        .score-bar {{ height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }}
        .score-fill {{ height: 100%; border-radius: 4px; }}
        .score-fill.high {{ background: #10b981; }}
        .score-fill.medium {{ background: #f59e0b; }}
        .score-fill.low {{ background: #ef4444; }}
        .trend-section {{
            background: white; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px; margin-top: 20px;
        }}
        .trend-section h2 {{ margin: 0 0 16px; color: #333; }}
        .trend-chart {{ height: 200px; background: #f8f9fa; border-radius: 8px; position: relative; }}
        .generated-time {{ text-align: center; color: #999; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{report.report_name}</h1>
            <p>生成时间: {datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="summary-cards">
            <div class="summary-card info">
                <div class="label">总测试数</div>
                <div class="value">{report.summary.total_tests}</div>
            </div>
            <div class="summary-card pass">
                <div class="label">通过数</div>
                <div class="value">{report.summary.passed_tests}</div>
            </div>
            <div class="summary-card fail">
                <div class="label">失败数</div>
                <div class="value">{report.summary.failed_tests}</div>
            </div>
            <div class="summary-card info">
                <div class="label">通过率</div>
                <div class="value">{report.summary.pass_rate}%</div>
            </div>
            <div class="summary-card info">
                <div class="label">平均分</div>
                <div class="value">{report.summary.average_score}</div>
            </div>
            <div class="summary-card info">
                <div class="label">总耗时</div>
                <div class="value">{report.summary.total_duration_ms:.2f}ms</div>
            </div>
        </div>

        <div class="test-list">
            <table>
                <thead>
                    <tr>
                        <th>测试ID</th>
                        <th>测试名称</th>
                        <th>类型</th>
                        <th>状态</th>
                        <th>得分</th>
                        <th>耗时</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(self._render_test_row(r) for r in report.results)}
                </tbody>
            </table>
        </div>

        {self._render_trend_section(report)}

        <div class="generated-time">
            报告生成于 {datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S')} | 版本 1.0.0
        </div>
    </div>
</body>
</html>
"""
        return html_template

    def _render_test_row(self, result: TestResult) -> str:
        """渲染测试结果行"""
        score_class = "high" if result.score >= 80 else "medium" if result.score >= 60 else "low"
        status_class = "status-pass" if result.passed else "status-fail"
        status_text = "通过" if result.passed else "失败"

        return f"""
<tr>
    <td>{result.test_id}</td>
    <td>{result.test_name}</td>
    <td>{result.test_type}</td>
    <td><span class="{status_class}">{status_text}</span></td>
    <td>
        <div style="display: flex; align-items: center; gap: 8px;">
            <div class="score-bar" style="flex: 1; max-width: 100px;">
                <div class="score-fill {score_class}" style="width: {result.score}%"></div>
            </div>
            <span style="font-weight: 600;">{result.score:.1f}</span>
        </div>
    </td>
    <td>{result.duration_ms:.2f}ms</td>
</tr>
"""

    def _render_trend_section(self, report: TestReport) -> str:
        """渲染趋势分析部分"""
        if not report.trends or len(report.trends) < 2:
            return ""

        # 计算图表坐标
        trends = report.trends
        max_score = 100
        min_score = 0
        chart_height = 180
        chart_width = 100

        # 生成SVG图表
        points_pass = []
        points_score = []

        for i, trend in enumerate(trends):
            x = (i / (len(trends) - 1)) * chart_width
            y_pass = chart_height - ((trend.pass_rate - min_score) / (max_score - min_score)) * chart_height
            y_score = chart_height - ((trend.average_score - min_score) / (max_score - min_score)) * chart_height
            points_pass.append(f"{x},{y_pass}")
            points_score.append(f"{x},{y_score}")

        pass_line = " ".join(points_pass)
        score_line = " ".join(points_score)

        # 计算渐变填充路径
        pass_first_y = points_pass[0].split(",")[1]
        score_first_y = points_score[0].split(",")[1]
        pass_fill_points = f"{pass_line},{chart_width},{chart_height},0,{chart_height},0,{pass_first_y}"
        score_fill_points = f"{score_line},{chart_width},{chart_height},0,{chart_height},0,{score_first_y}"

        return f"""
<div class="trend-section">
    <h2>趋势分析</h2>
    <div class="trend-chart">
        <svg viewBox="0 0 {chart_width} {chart_height}" style="width: 100%; height: 100%;">
            <defs>
                <linearGradient id="passGradient" x1="0%" y1="0%" x2="0%" y2="100%">  # noqa: E226
                    <stop offset="0%" style="stop-color:#10b981;stop-opacity:0.3" />  # noqa: E226
                    <stop offset="100%" style="stop-color:#10b981;stop-opacity:0" />  # noqa: E226
                </linearGradient>
                <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="0%" y2="100%">  # noqa: E226
                    <stop offset="0%" style="stop-color:#3b82f6;stop-opacity:0.3" />  # noqa: E226
                    <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:0" />  # noqa: E226
                </linearGradient>
            </defs>
            <polyline points="{pass_line}" fill="none" stroke="#10b981" stroke-width="2" />
            <polyline points="{pass_fill_points}" fill="url(#passGradient)" />
            <polyline points="{score_line}" fill="none" stroke="#3b82f6" stroke-width="2" />
            <polyline points="{score_fill_points}" fill="url(#scoreGradient)" />
            <text x="2" y="12" font-size="8" fill="#666">通过率</text>
            <text x="2" y="24" font-size="8" fill="#666">平均分</text>
            <line x1="0" y1="{chart_height - (80/100)*chart_height}"
                  x2="{chart_width}" y2="{chart_height - (80/100)*chart_height}"
                  stroke="#ddd" stroke-width="0.5" stroke-dasharray="2,2" />
            <line x1="0" y1="{chart_height - (60/100)*chart_height}"
                  x2="{chart_width}" y2="{chart_height - (60/100)*chart_height}"
                  stroke="#ddd" stroke-width="0.5" stroke-dasharray="2,2" />
            <text x="2" y="{chart_height - (80/100)*chart_height + 4}" font-size="6" fill="#999">80</text>
            <text x="2" y="{chart_height - (60/100)*chart_height + 4}" font-size="6" fill="#999">60</text>
        </svg>
    </div>
</div>
"""

    def get_history(self, limit: int = 100) -> List[TestHistory]:
        """获取测试历史记录

        Args:
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        return sorted(self.history_store, key=lambda x: x.timestamp, reverse=True)[:limit]
