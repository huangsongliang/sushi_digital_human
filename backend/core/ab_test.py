"""
A/B 测试框架
支持不同检索策略、提示词和模型参数的对比测试
"""

import hashlib
import time
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from backend.utils.logger import get_logger

logger = get_logger(__name__)
assert logger is not None, "Logger cannot be None"


class ExperimentType(Enum):
    """实验类型"""

    RETRIEVAL_STRATEGY = "retrieval_strategy"
    PROMPT_TEMPLATE = "prompt_template"
    MODEL_PARAMS = "model_params"
    RERANKING = "reranking"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    """实验状态"""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class ExperimentVariant:
    """实验变体（对照组/实验组）"""

    variant_id: str
    name: str
    description: str
    config: Dict[str, Any]
    traffic_percentage: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    """A/B 测试实验"""

    experiment_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    variants: List[ExperimentVariant]
    status: ExperimentStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    target_metric: str = "user_satisfaction"
    minimum_sample_size: int = 100

    def get_variant_by_id(self, variant_id: str) -> Optional[ExperimentVariant]:
        """根据 ID 获取变体"""
        for variant in self.variants:
            if variant.variant_id == variant_id:
                return variant
        return None


@dataclass
class ExperimentResult:
    """实验结果"""

    experiment_id: str
    variant_id: str
    timestamp: datetime
    session_id: str
    user_id: Optional[str] = None
    query: str = ""
    input_config: Dict[str, Any] = field(default_factory=dict)
    output_config: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    feedback: Optional[int] = None


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._results: Dict[str, List[ExperimentResult]] = {}
        self._user_assignments: Dict[str, str] = {}

    def create_experiment(
        self,
        name: str,
        description: str,
        experiment_type: ExperimentType,
        variants: List[Dict[str, Any]],
        target_metric: str = "user_satisfaction",
        minimum_sample_size: int = 100,
    ) -> Experiment:
        """创建 A/B 测试实验"""
        experiment_id = self._generate_experiment_id(name)
        total_traffic = sum(v.get("traffic_percentage", 0) for v in variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"变体流量分配总和必须为 100%，当前为 {total_traffic}%")

        experiment_variants = [
            ExperimentVariant(
                variant_id=self._generate_variant_id(experiment_id, i),
                name=v["name"],
                description=v.get("description", ""),
                config=v.get("config", {}),
                traffic_percentage=v.get("traffic_percentage", 0),
            )
            for i, v in enumerate(variants)
        ]

        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            experiment_type=experiment_type,
            variants=experiment_variants,
            status=ExperimentStatus.DRAFT,
            target_metric=target_metric,
            minimum_sample_size=minimum_sample_size,
        )

        self._experiments[experiment_id] = experiment
        self._results[experiment_id] = []

        logger.info(f"创建 A/B 测试实验: {name} ({experiment_id})")
        return experiment

    def start_experiment(self, experiment_id: str) -> bool:
        """启动实验"""
        if experiment_id not in self._experiments:
            logger.error(f"实验不存在: {experiment_id}")
            return False

        experiment = self._experiments[experiment_id]
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_time = datetime.now()

        logger.info(f"启动实验: {experiment.name}")
        return True

    def pause_experiment(self, experiment_id: str) -> bool:
        """暂停实验"""
        if experiment_id not in self._experiments:
            return False

        experiment = self._experiments[experiment_id]
        experiment.status = ExperimentStatus.PAUSED

        logger.info(f"暂停实验: {experiment.name}")
        return True

    def complete_experiment(self, experiment_id: str) -> bool:
        """完成实验"""
        if experiment_id not in self._experiments:
            return False

        experiment = self._experiments[experiment_id]
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_time = datetime.now()

        logger.info(f"完成实验: {experiment.name}")
        return True

    def assign_variant(
        self,
        experiment_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Optional[ExperimentVariant]:
        """为用户分配实验变体"""
        if experiment_id not in self._experiments:
            return None

        experiment = self._experiments[experiment_id]
        if experiment.status != ExperimentStatus.RUNNING:
            return None

        anon_id = f"anonymous_{random.randint(1000, 9999)}"
        assign_key = user_id or session_id or anon_id
        cache_key = f"{experiment_id}:{assign_key}"

        if cache_key in self._user_assignments:
            variant_id = self._user_assignments[cache_key]
            return experiment.get_variant_by_id(variant_id)

        traffic = self._calculate_traffic_hash(assign_key)
        cumulative = 0.0

        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if traffic < cumulative:
                self._user_assignments[cache_key] = variant.variant_id
                logger.debug(f"为 {assign_key} 分配变体: {variant.name}")
                return variant

        return experiment.variants[0] if experiment.variants else None

    def record_result(self, result: ExperimentResult) -> bool:
        """记录实验结果"""
        if result.experiment_id not in self._experiments:
            return False

        self._results[result.experiment_id].append(result)

        experiment = self._experiments[result.experiment_id]
        variant = experiment.get_variant_by_id(result.variant_id)
        if variant:
            self._update_variant_metrics(variant, result)

        return True

    def _update_variant_metrics(
        self, variant: ExperimentVariant, result: ExperimentResult
    ):
        """更新变体指标"""
        if "total_count" not in variant.metrics:
            variant.metrics["total_count"] = 0
            variant.metrics["total_score"] = 0.0
            variant.metrics["avg_score"] = 0.0

        variant.metrics["total_count"] += 1

        if result.feedback is not None:
            variant.metrics["total_score"] += result.feedback
            variant.metrics["avg_score"] = (
                variant.metrics["total_score"] / variant.metrics["total_count"]
            )

        if "response_times" not in variant.metrics:
            variant.metrics["response_times"] = []

        if "response_time" in result.metrics:
            variant.metrics["response_times"].append(result.metrics["response_time"])

    def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验结果分析"""
        if experiment_id not in self._experiments:
            return {}

        experiment = self._experiments[experiment_id]
        results = self._results[experiment_id]

        variant_stats = {}
        for variant in experiment.variants:
            variant_results = [r for r in results if r.variant_id == variant.variant_id]

            total_count = len(variant_results)
            avg_score = sum(r.feedback or 0 for r in variant_results) / max(
                total_count, 1
            )

            response_times = [
                r.metrics.get("response_time", 0)
                for r in variant_results
                if "response_time" in r.metrics
            ]
            avg_response_time = sum(response_times) / max(len(response_times), 1)

            variant_stats[variant.variant_id] = {
                "variant_name": variant.name,
                "total_count": total_count,
                "avg_score": round(avg_score, 2),
                "avg_response_time": round(avg_response_time, 2),
                "sample_size_met": (total_count >= experiment.minimum_sample_size),
            }

        significance = self._calculate_significance(experiment, variant_stats)

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "status": experiment.status.value,
            "total_samples": len(results),
            "minimum_sample_size": experiment.minimum_sample_size,
            "variant_stats": variant_stats,
            "significance": significance,
            "recommendation": self._generate_recommendation(
                variant_stats, significance
            ),
        }

    def _calculate_significance(
        self, experiment: Experiment, variant_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算统计显著性"""
        if len(experiment.variants) < 2:
            return {"is_significant": False, "confidence_level": 0}

        control_variant = max(experiment.variants, key=lambda v: v.traffic_percentage)
        control_stats = variant_stats.get(control_variant.variant_id, {})

        if not control_stats.get("sample_size_met"):
            return {"is_significant": False, "confidence_level": 0}

        improvements = []
        for variant in experiment.variants:
            if variant.variant_id == control_variant.variant_id:
                continue

            variant_stat = variant_stats.get(variant.variant_id, {})
            if not variant_stat.get("sample_size_met"):
                continue

            control_score = control_stats.get("avg_score", 0)
            variant_score = variant_stat.get("avg_score", 0)

            if control_score > 0:
                improvement = ((variant_score - control_score) / control_score) * 100
                improvements.append(
                    {
                        "variant_id": variant.variant_id,
                        "variant_name": variant.name,
                        "improvement_percent": round(improvement, 2),
                    }
                )

        max_improvement = max(
            (i["improvement_percent"] for i in improvements), default=0
        )
        is_significant = abs(max_improvement) > 5

        return {
            "is_significant": is_significant,
            "confidence_level": min(95, 50 + abs(max_improvement) * 2),
            "improvements": improvements,
        }

    def _generate_recommendation(
        self, variant_stats: Dict[str, Any], significance: Dict[str, Any]
    ) -> str:
        """生成推荐建议"""
        if not significance.get("is_significant"):
            return "样本量不足或差异不显著，建议继续收集数据"

        improvements = significance.get("improvements", [])
        if not improvements:
            return "未发现显著差异"

        best = max(improvements, key=lambda x: x["improvement_percent"])
        if best["improvement_percent"] > 0:
            return "变体 '{}' 表现最佳，建议推广".format(best["variant_name"])
        else:
            return "对照组表现最佳，建议继续使用当前方案"

    def _calculate_traffic_hash(self, key: str) -> float:
        """根据哈希分配流量"""
        hash_value = hashlib.md5(f"{key}{time.time()}".encode()).hexdigest()
        return (int(hash_value[:8], 16) % 10000) / 100.0

    def _generate_experiment_id(self, name: str) -> str:
        """生成实验 ID"""
        hash_input = f"{name}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def _generate_variant_id(self, experiment_id: str, index: int) -> str:
        """生成变体 ID"""
        return f"{experiment_id}_variant_{index}"

    def get_all_experiments(self) -> List[Dict[str, Any]]:
        """获取所有实验列表"""
        return [
            {
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "description": exp.description,
                "type": exp.experiment_type.value,
                "status": exp.status.value,
                "variant_count": len(exp.variants),
                "sample_count": len(self._results.get(exp.experiment_id, [])),
            }
            for exp in self._experiments.values()
        ]


ab_test_manager = ABTestManager()


def get_ab_test_manager() -> ABTestManager:
    """获取 A/B 测试管理器"""
    return ab_test_manager
