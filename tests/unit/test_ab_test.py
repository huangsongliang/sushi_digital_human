"""
A/B 测试模块单元测试
"""

import pytest
from backend.core.ab_test import (
    ABTestManager,
    ExperimentType,
    ExperimentStatus,
    ExperimentVariant,
    ExperimentResult
)


class TestABTestManager:
    """A/B 测试管理器测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.manager = ABTestManager()
    
    def test_create_experiment(self):
        """测试创建实验"""
        experiment = self.manager.create_experiment(
            name="检索策略对比测试",
            description="对比不同检索策略的效果",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {
                    "name": "BM25",
                    "description": "BM25 检索",
                    "traffic_percentage": 50,
                    "config": {"use_bm25": True, "use_vector": False}
                },
                {
                    "name": "向量检索",
                    "description": "向量检索",
                    "traffic_percentage": 50,
                    "config": {"use_bm25": False, "use_vector": True}
                }
            ]
        )
        
        assert experiment is not None
        assert experiment.name == "检索策略对比测试"
        assert len(experiment.variants) == 2
        assert experiment.status == ExperimentStatus.DRAFT
    
    def test_create_experiment_invalid_traffic(self):
        """测试创建实验时流量分配无效"""
        with pytest.raises(ValueError):
            self.manager.create_experiment(
                name="测试实验",
                description="测试",
                experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
                variants=[
                    {"name": "A", "traffic_percentage": 30},
                    {"name": "B", "traffic_percentage": 30}  # 总和为 60%，不是 100%
                ]
            )
    
    def test_start_experiment(self):
        """测试启动实验"""
        experiment = self.manager.create_experiment(
            name="测试实验",
            description="测试",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {"name": "A", "traffic_percentage": 50},
                {"name": "B", "traffic_percentage": 50}
            ]
        )
        
        success = self.manager.start_experiment(experiment.experiment_id)
        assert success is True
        assert experiment.status == ExperimentStatus.RUNNING
        assert experiment.start_time is not None
    
    def test_assign_variant(self):
        """测试分配变体"""
        experiment = self.manager.create_experiment(
            name="测试实验",
            description="测试",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {"name": "A", "traffic_percentage": 50},
                {"name": "B", "traffic_percentage": 50}
            ]
        )
        
        self.manager.start_experiment(experiment.experiment_id)
        
        # 同一用户应分配到相同变体
        variant1 = self.manager.assign_variant(experiment.experiment_id, session_id="session_1")
        variant2 = self.manager.assign_variant(experiment.experiment_id, session_id="session_1")
        
        assert variant1 is not None
        assert variant2 is not None
        assert variant1.variant_id == variant2.variant_id
    
    def test_record_result(self):
        """测试记录结果"""
        from datetime import datetime
        
        experiment = self.manager.create_experiment(
            name="测试实验",
            description="测试",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {"name": "A", "traffic_percentage": 50},
                {"name": "B", "traffic_percentage": 50}
            ]
        )
        
        self.manager.start_experiment(experiment.experiment_id)
        variant = experiment.variants[0]
        
        result = ExperimentResult(
            experiment_id=experiment.experiment_id,
            variant_id=variant.variant_id,
            timestamp=datetime.now(),
            session_id="session_1",
            query="测试问题",
            metrics={"response_time": 1.5}
        )
        result.feedback = 4
        
        success = self.manager.record_result(result)
        assert success is True
        assert variant.metrics["total_count"] == 1
        assert variant.metrics["avg_score"] == 4.0
    
    def test_get_experiment_results(self):
        """测试获取实验结果"""
        from datetime import datetime
        
        experiment = self.manager.create_experiment(
            name="测试实验",
            description="测试",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {"name": "A", "traffic_percentage": 50},
                {"name": "B", "traffic_percentage": 50}
            ]
        )
        
        self.manager.start_experiment(experiment.experiment_id)
        
        # 添加多个结果
        for i in range(10):
            variant = experiment.variants[i % 2]
            result = ExperimentResult(
                experiment_id=experiment.experiment_id,
                variant_id=variant.variant_id,
                timestamp=datetime.now(),
                session_id=f"session_{i}"
            )
            result.feedback = 4 if i % 2 == 0 else 3
            self.manager.record_result(result)
        
        results = self.manager.get_experiment_results(experiment.experiment_id)
        
        assert results["total_samples"] == 10
        assert "variant_stats" in results
        assert "significance" in results
        assert "recommendation" in results
    
    def test_pause_and_complete_experiment(self):
        """测试暂停和完成实验"""
        experiment = self.manager.create_experiment(
            name="测试实验",
            description="测试",
            experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
            variants=[
                {"name": "A", "traffic_percentage": 50},
                {"name": "B", "traffic_percentage": 50}
            ]
        )
        
        self.manager.start_experiment(experiment.experiment_id)
        self.manager.pause_experiment(experiment.experiment_id)
        assert experiment.status == ExperimentStatus.PAUSED
        
        self.manager.start_experiment(experiment.experiment_id)
        self.manager.complete_experiment(experiment.experiment_id)
        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.end_time is not None
    
    def test_get_all_experiments(self):
        """测试获取所有实验"""
        # 创建多个实验
        for i in range(3):
            self.manager.create_experiment(
                name=f"测试实验{i}",
                description="测试",
                experiment_type=ExperimentType.RETRIEVAL_STRATEGY,
                variants=[
                    {"name": "A", "traffic_percentage": 50},
                    {"name": "B", "traffic_percentage": 50}
                ]
            )
        
        experiments = self.manager.get_all_experiments()
        assert len(experiments) == 3
