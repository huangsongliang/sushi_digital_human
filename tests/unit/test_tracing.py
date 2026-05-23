"""溯源追踪模块单元测试"""

from datetime import datetime

import pytest
from backend.utils.tracing import (
    RetrievedDocument,
    TraceRecord,
    TraceStep,
)


class TestTraceStep:
    """TraceStep 测试"""

    def test_step_creation(self):
        step = TraceStep(
            step_id="s1",
            step_type="retrieval",
            content="检索到 5 篇文档",
            timestamp=datetime.now(),
            confidence=0.85,
        )
        assert step.step_id == "s1"
        assert step.step_type == "retrieval"
        assert step.content == "检索到 5 篇文档"
        assert step.confidence == 0.85
        assert step.timestamp is not None

    def test_step_defaults(self):
        step = TraceStep(
            step_id="s1",
            step_type="question",
            content="测试",
            timestamp=datetime.now(),
        )
        assert step.confidence == 0.0
        assert step.metadata is None


class TestRetrievedDocument:
    """RetrievedDocument 测试"""

    def test_doc_creation(self):
        doc = RetrievedDocument(
            doc_id="d1",
            title="测试文档",
            content="文档内容",
            source="local",
            score=0.95,
        )
        assert doc.doc_id == "d1"
        assert doc.title == "测试文档"
        assert doc.score == 0.95
        assert doc.source == "local"


class TestTraceRecord:
    """TraceRecord 测试"""

    def test_record_creation(self):
        step = TraceStep(
            step_id="s1",
            step_type="question",
            content="Q",
            timestamp=datetime.now(),
        )
        record = TraceRecord(
            trace_id="t1",
            question="测试问题",
            answer="测试答案",
            steps=[step],
            retrieved_docs=[],
        )
        assert record.trace_id == "t1"
        assert record.question == "测试问题"
        assert record.answer == "测试答案"
        assert len(record.steps) == 1
        assert record.retrieved_docs == []

    def test_record_to_dict(self):
        step = TraceStep(
            step_id="s1",
            step_type="question",
            content="Q",
            timestamp=datetime.now(),
        )
        record = TraceRecord(
            trace_id="t1",
            question="Q",
            answer="A",
            steps=[step],
            retrieved_docs=[],
        )
        data = record.to_dict()
        assert data["trace_id"] == "t1"
        assert data["question"] == "Q"
        assert len(data["steps"]) == 1

    def test_record_add_steps(self):
        step1 = TraceStep(
            step_id="s1",
            step_type="question",
            content="Q",
            timestamp=datetime.now(),
        )
        record = TraceRecord(
            trace_id="t2",
            question="Q",
            answer="A",
            steps=[step1],
            retrieved_docs=[],
        )
        step2 = TraceStep(
            step_id="s2",
            step_type="retrieval",
            content="检索完成",
            timestamp=datetime.now(),
        )
        record.steps.append(step2)
        assert len(record.steps) == 2
