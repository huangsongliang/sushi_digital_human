"""Prompt调试模块 - 提供Prompt注入检测、模板调试和Token使用分析功能"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TokenUsage:
    """Token使用统计"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


@dataclass
class PromptAnalysis:
    """Prompt分析结果"""

    injection_detected: bool = False
    injection_patterns: List[str] = None
    token_count: int = 0
    template_variables: List[str] = None
    template_errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None

    def __post_init__(self):
        if self.injection_patterns is None:
            self.injection_patterns = []
        if self.template_variables is None:
            self.template_variables = []
        if self.template_errors is None:
            self.template_errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


class PromptDebugger:
    """Prompt调试器 - 提供Prompt分析和调试功能"""

    INJECTION_PATTERNS = [
        r"(?i)(?:system|assistant|user):",
        r"(?i)ignore.*previous.*instructions?",
        r"(?i)override.*instructions?",
        r"(?i)reset.*context?",
        r"(?i)forget.*previous.*prompt?",
        r"(?i)execute.*command?",
        r"(?i)run.*code?",
        r"(?i)\{\{.*\}\}",
        r"(?i)<script.*>",
        r"(?i)javascript:",
        r"(?i)drop.*table",
        r"(?i)union.*select",
        r"(?i);.*--",
    ]

    def __init__(self):
        self.patterns = [re.compile(pattern) for pattern in self.INJECTION_PATTERNS]

    def analyze_prompt(self, prompt: str, template_variables: Optional[Dict[str, Any]] = None) -> PromptAnalysis:
        """分析Prompt，检测注入和问题"""
        analysis = PromptAnalysis()

        self._detect_injection(prompt, analysis)
        self._count_tokens(prompt, analysis)
        self._extract_variables(prompt, analysis)
        self._validate_template(prompt, template_variables, analysis)
        self._generate_suggestions(prompt, analysis)

        return analysis

    def _detect_injection(self, prompt: str, analysis: PromptAnalysis):
        """检测Prompt注入攻击"""
        for pattern in self.patterns:
            if pattern.search(prompt):
                analysis.injection_detected = True
                analysis.injection_patterns.append(pattern.pattern)
                logger.warning(f"Prompt injection detected: {pattern.pattern}")

        if analysis.injection_detected:
            analysis.warnings.append("检测到潜在的Prompt注入攻击")

    def _count_tokens(self, prompt: str, analysis: PromptAnalysis):
        """估算Token数量"""
        analysis.token_count = self.count_tokens(prompt)

        if analysis.token_count > 3000:
            analysis.warnings.append(f"Token数量较高 ({analysis.token_count})，建议优化")

    def _extract_variables(self, prompt: str, analysis: PromptAnalysis):
        """提取模板变量"""
        # 匹配 {{variable}} 或 {variable} 格式的变量
        patterns = [r"\{\{(\w+)\}\}", r"\{(\w+)\}"]
        for pattern in patterns:
            matches = re.findall(pattern, prompt)
            analysis.template_variables.extend(matches)

        analysis.template_variables = list(set(analysis.template_variables))

    def _validate_template(self, prompt: str, template_variables: Optional[Dict[str, Any]], analysis: PromptAnalysis):
        """验证模板变量是否完整"""
        if not template_variables:
            template_variables = {}

        for var in analysis.template_variables:
            if var not in template_variables:
                analysis.template_errors.append(f"缺失模板变量: {var}")
                analysis.warnings.append(f"模板变量 '{var}' 未提供值")

    def _generate_suggestions(self, prompt: str, analysis: PromptAnalysis):
        """生成优化建议"""
        if analysis.token_count > 4000:
            analysis.suggestions.append("考虑将Prompt拆分为多个请求或使用更简洁的表述")

        if len(analysis.template_errors) > 0:
            analysis.suggestions.append("请确保所有模板变量都已正确赋值")

        if analysis.injection_detected:
            analysis.suggestions.append("建议对用户输入进行清洗和验证")

        if len(prompt) > 10000:
            analysis.suggestions.append("Prompt长度较长，考虑使用RAG检索相关上下文")

    def count_tokens(self, text: str) -> int:
        """估算文本的Token数量（简单估算：1 Token ≈ 4 字符）"""
        return len(text) // 4

    def debug_template(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """调试Prompt模板渲染"""
        try:
            rendered = template.format(**variables)
            return {
                "success": True,
                "rendered_prompt": rendered,
                "token_count": self.count_tokens(rendered),
                "variables_used": list(variables.keys()),
            }
        except KeyError as e:
            return {
                "success": False,
                "error": str(e),
                "missing_variable": str(e).strip("'"),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def analyze_token_usage(self, prompt: str, completion: Optional[str] = None) -> TokenUsage:
        """分析Token使用情况"""
        prompt_tokens = self.count_tokens(prompt)
        completion_tokens = self.count_tokens(completion) if completion else 0
        total_tokens = prompt_tokens + completion_tokens

        estimated_cost = self._estimate_cost(prompt_tokens, completion_tokens)

        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """估算API调用成本（基于常见模型定价）"""
        prompt_cost_per_1k = 0.0015
        completion_cost_per_1k = 0.002

        return (prompt_tokens / 1000 * prompt_cost_per_1k) + (completion_tokens / 1000 * completion_cost_per_1k)

    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """验证Prompt的格式和内容"""
        issues = []

        if not prompt or not prompt.strip():
            issues.append({"type": "error", "message": "Prompt不能为空"})

        if len(prompt) > 50000:
            issues.append({"type": "warning", "message": "Prompt长度超过50000字符，可能超出模型限制"})

        if len(prompt) < 10:
            issues.append({"type": "warning", "message": "Prompt过短，可能影响模型输出质量"})

        if any(char in prompt for char in ["\x00", "\x01", "\x02"]):
            issues.append({"type": "error", "message": "Prompt包含非法字符"})

        return {
            "valid": len([i for i in issues if i["type"] == "error"]) == 0,
            "issues": issues,
        }


prompt_debugger = PromptDebugger()
