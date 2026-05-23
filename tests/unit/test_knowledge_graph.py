"""知识图谱模块单元测试"""

import pytest
from backend.knowledge_graph.graph_query import GraphQuery
from backend.knowledge_graph.relation_extractor import Relation, RelationExtractor
from backend.knowledge_graph.ner_extractor import Entity, NERExtractor


class TestRelation:
    """Relation 模型测试"""

    def test_relation_creation(self):
        rel = Relation(
            source="张三",
            source_type="PERSON",
            target="北京",
            target_type="LOCATION",
            relation_type="LIVES_IN",
            confidence=0.9,
            context="张三住在北京",
        )
        assert rel.source == "张三"
        assert rel.target == "北京"
        assert rel.relation_type == "LIVES_IN"
        assert rel.confidence == 0.9
        assert rel.context == "张三住在北京"


class TestRelationExtractor:
    """RelationExtractor 测试"""

    def test_extractor_creation(self):
        extractor = RelationExtractor()
        assert extractor is not None
        assert isinstance(extractor._patterns, dict)

    def test_extract_relations_empty_text(self):
        extractor = RelationExtractor()
        results = extractor.extract_relations("")
        assert results == []

    def test_extract_relations_basic(self):
        extractor = RelationExtractor()
        text = "张三在北京工作。"
        results = extractor.extract_relations(text)
        assert isinstance(results, list)


class TestEntity:
    """Entity 模型测试"""

    def test_entity_creation(self):
        entity = Entity(
            text="张三",
            label="PERSON",
            start=0,
            end=2,
            confidence=0.95,
        )
        assert entity.text == "张三"
        assert entity.label == "PERSON"
        assert entity.confidence == 0.95


class TestNERExtractor:
    """NERExtractor 测试"""

    def test_extractor_creation(self):
        extractor = NERExtractor()
        assert extractor is not None

    def test_extract_entities_empty_text(self):
        extractor = NERExtractor()
        results = extractor.extract_entities("")
        assert results == []

    def test_extract_entities_basic(self):
        extractor = NERExtractor()
        text = "张三和李四在北京见面。"
        results = extractor.extract_entities(text)
        assert isinstance(results, list)


class TestGraphQuery:
    """GraphQuery 测试"""

    def test_query_creation(self):
        query = GraphQuery()
        assert query is not None

    def test_find_neighbors_no_storage(self):
        query = GraphQuery()
        neighbors = query.find_neighbors("test_node")
        assert isinstance(neighbors, dict)

    def test_find_path_no_storage(self):
        query = GraphQuery()
        path = query.find_path("node_a", "node_b")
        assert isinstance(path, list)
