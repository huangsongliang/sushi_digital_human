"""溯源追踪模块单元测试"""

import pytest
from backend.utils.tracing import TraceStep, RetrievedDocument, TraceRecord


class TestTraceStep:
    """TraceStep 测试"""

    def test_step_creation(self):
        step = TraceStep(
            step_id="s1",
            step_type="retrieval",
            content="检索到 5 篇文档",
            confidence=0.85,
        )
        assert step.step_id == "s1"
        assert step.step_type == "retrieval"
        assert step.content == "检索到 5 篇文档"
        assert step.confidence == 0.85
        assert step.timestamp is not None

    def test_step_defaults(self):
        step = TraceStep(step_id="s1", step_type="question", content="测试")
        assert step.confidence == 1.0
        assert step.metadata == {}


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
        record = TraceRecord(
            trace_id="t1",
            question="测试问题",
            answer="测试答案",
        )
        assert record.trace_id == "t1"
        assert record.question == "测试问题"
        assert record.answer == "测试答案"
        assert record.steps == []
        assert record.retrieved_docs == []
        assert record.latency is not None

    def test_record_to_dict(self):
        record = TraceRecord(
            trace_id="t1",
            question="Q",
            answer="A",
            steps=[
                TraceStep(step_id="s1", step_type="question", content="Q"),
            ],
        )
        data = record.to_dict()
        assert data["trace_id"] == "t1"
        assert data["question"] == "Q"
        assert len(data["steps"]) == 1

    def test_record_add_steps(self):
        record = TraceRecord(trace_id="t2", question="Q", answer="A")
        record.steps.append(TraceStep(step_id="s1", step_type="retrieval", content="检索完成"))
        assert len(record.steps) == 1
