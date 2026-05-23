"""告警规则引擎
支持阈值规则、趋势规则、复合规则
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from backend.monitoring.metrics_collector import get_metrics_collector
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class RuleType(str, Enum):
    """规则类型"""

    THRESHOLD = "threshold"
    TREND = "trend"
    COMPOSITE = "composite"
    ANOMALY = "anomaly"


class ComparisonOperator(str, Enum):
    """比较运算符"""

    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="
    NE = "!="
    CONTAINS = "contains"


class AlertLevel(str, Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class RuleCondition:
    """规则条件"""

    metric_name: str
    operator: ComparisonOperator
    threshold: float
    window_seconds: int = 300


@dataclass
class AlertRule:
    """告警规则"""

    id: str
    name: str
    description: str
    rule_type: RuleType
    conditions: List[RuleCondition]
    alert_level: AlertLevel
    enabled: bool = True
    cooldown_seconds: int = 300
    created_at: float = field(default_factory=time.time)
    last_triggered_at: float = 0
    trigger_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())


class RuleEngine:
    """规则引擎"""

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.triggered_rules: Dict[str, float] = {}
        self.metrics_collector = get_metrics_collector()

    def add_rule(self, rule: AlertRule) -> bool:
        """添加规则"""
        try:
            self.rules[rule.id] = rule
            logger.info(f"规则添加成功: {rule.name} (id={rule.id})")
            return True
        except Exception as e:
            logger.error(f"添加规则失败: {str(e)}")
            return False

    def remove_rule(self, rule_id: str) -> bool:
        """移除规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"规则移除成功: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False

    def check_rule(self, rule: AlertRule) -> bool:
        """检查单个规则"""
        if not rule.enabled:
            return False

        if time.time() - rule.last_triggered_at < rule.cooldown_seconds:
            return False

        for condition in rule.conditions:
            if not self._check_condition(condition):
                return False

        return True

    def _check_condition(self, condition: RuleCondition) -> bool:
        """检查条件"""
        stats = self.metrics_collector.get_metric_statistics(
            condition.metric_name,
            window_seconds=condition.window_seconds
        )

        if not stats or stats["count"] == 0:
            return False

        latest_value = stats["latest"]

        operators = {
            ComparisonOperator.GT: lambda x, y: x > y,
            ComparisonOperator.GTE: lambda x, y: x >= y,
            ComparisonOperator.LT: lambda x, y: x < y,
            ComparisonOperator.LTE: lambda x, y: x <= y,
            ComparisonOperator.EQ: lambda x, y: x == y,
            ComparisonOperator.NE: lambda x, y: x != y,
        }

        if condition.operator in operators:
            return operators[condition.operator](latest_value, condition.threshold)

        return False

    def evaluate_all_rules(self) -> List[AlertRule]:
        """评估所有规则"""
        triggered_rules = []

        for rule in self.rules.values():
            if self.check_rule(rule):
                rule.last_triggered_at = time.time()
                rule.trigger_count += 1
                triggered_rules.append(rule)
                logger.info(f"规则触发: {rule.name}, level={rule.alert_level}")

        return triggered_rules

    def create_threshold_rule(
        self,
        name: str,
        metric_name: str,
        operator: ComparisonOperator,
        threshold: float,
        alert_level: AlertLevel,
        description: str = "",
        window_seconds: int = 300,
        cooldown_seconds: int = 300,
    ) -> AlertRule:
        """创建阈值规则"""
        rule = AlertRule(
            id=str(uuid4()),
            name=name,
            description=description or f"{metric_name} {operator.value} {threshold}",
            rule_type=RuleType.THRESHOLD,
            conditions=[
                RuleCondition(
                    metric_name=metric_name,
                    operator=operator,
                    threshold=threshold,
                    window_seconds=window_seconds,
                )
            ],
            alert_level=alert_level,
            cooldown_seconds=cooldown_seconds,
        )

        self.add_rule(rule)
        return rule

    def create_trend_rule(
        self,
        name: str,
        metric_name: str,
        threshold_percent: float,
        alert_level: AlertLevel,
        description: str = "",
        window_seconds: int = 300,
        cooldown_seconds: int = 300,
    ) -> AlertRule:
        """创建趋势规则"""
        condition = RuleCondition(
            metric_name=metric_name,
            operator=ComparisonOperator.GT,
            threshold=threshold_percent,
            window_seconds=window_seconds,
        )

        rule = AlertRule(
            id=str(uuid4()),
            name=name,
            description=description or f"{metric_name} 趋势超过 {threshold_percent}%",
            rule_type=RuleType.TREND,
            conditions=[condition],
            alert_level=alert_level,
            cooldown_seconds=cooldown_seconds,
        )

        self.add_rule(rule)
        return rule

    def get_all_rules(self) -> List[AlertRule]:
        """获取所有规则"""
        return list(self.rules.values())

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取规则"""
        return self.rules.get(rule_id)

    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则统计"""
        stats = {
            "total": len(self.rules),
            "enabled": sum(1 for r in self.rules.values() if r.enabled),
            "disabled": sum(1 for r in self.rules.values() if not r.enabled),
            "by_level": {},
            "by_type": {},
        }

        for rule in self.rules.values():
            level = rule.alert_level.value
            rule_type = rule.rule_type.value

            if level not in stats["by_level"]:
                stats["by_level"][level] = 0
            stats["by_level"][level] += 1

            if rule_type not in stats["by_type"]:
                stats["by_type"][rule_type] = 0
            stats["by_type"][rule_type] += 1

        return stats

    def export_rules(self) -> List[Dict[str, Any]]:
        """导出规则配置"""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type.value,
                "conditions": [
                    {
                        "metric_name": cond.metric_name,
                        "operator": cond.operator.value,
                        "threshold": cond.threshold,
                        "window_seconds": cond.window_seconds,
                    }
                    for cond in rule.conditions
                ],
                "alert_level": rule.alert_level.value,
                "enabled": rule.enabled,
                "cooldown_seconds": rule.cooldown_seconds,
            }
            for rule in self.rules.values()
        ]

    def import_rules(self, rules_config: List[Dict[str, Any]]) -> int:
        """导入规则配置"""
        imported_count = 0

        for config in rules_config:
            try:
                conditions = [
                    RuleCondition(
                        metric_name=cond["metric_name"],
                        operator=ComparisonOperator(cond["operator"]),
                        threshold=cond["threshold"],
                        window_seconds=cond.get("window_seconds", 300),
                    )
                    for cond in config.get("conditions", [])
                ]

                rule = AlertRule(
                    id=config["id"],
                    name=config["name"],
                    description=config.get("description", ""),
                    rule_type=RuleType(config["rule_type"]),
                    conditions=conditions,
                    alert_level=AlertLevel(config["alert_level"]),
                    enabled=config.get("enabled", True),
                    cooldown_seconds=config.get("cooldown_seconds", 300),
                )

                self.add_rule(rule)
                imported_count += 1

            except Exception as e:
                logger.error(f"导入规则失败: {config.get('name', 'unknown')}: {str(e)}")

        return imported_count


_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """获取规则引擎实例"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
        logger.info("规则引擎已初始化")
    return _rule_engine
