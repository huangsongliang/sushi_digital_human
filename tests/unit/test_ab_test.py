"""AB测试模块单元测试"""
from backend.core.ab_test import (
    ExperimentVariant,
    ExperimentType,
    ExperimentStatus
)


class TestExperimentVariant:
    """变体测试"""

    def test_variant_creation(self):
        variant = ExperimentVariant(
            variant_id="v1",
            name="variant_a",
            description="Test variant",
            config={"param": "value"},
            traffic_percentage=50.0
        )
        assert variant.variant_id == "v1"
        assert variant.name == "variant_a"
        assert variant.traffic_percentage == 50.0


class TestExperimentType:
    """实验类型枚举测试"""

    def test_experiment_types(self):
        assert ExperimentType.RETRIEVAL_STRATEGY.value == "retrieval_strategy"
        assert ExperimentType.PROMPT_TEMPLATE.value == "prompt_template"
        assert ExperimentType.MODEL_PARAMS.value == "model_params"


class TestExperimentStatus:
    """实验状态枚举测试"""

    def test_experiment_status(self):
        assert ExperimentStatus.DRAFT.value == "draft"
        assert ExperimentStatus.RUNNING.value == "running"
        assert ExperimentStatus.PAUSED.value == "paused"
        assert ExperimentStatus.COMPLETED.value == "completed"
