"""
问答溯源模块
提供完整的问答溯源功能，支持：
- 记录问答全过程
- 显示回答来源和推理路径
- 支持用户查看引用文档
- 提供可解释性
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TraceStep:
    """溯源步骤"""

    step_id: str
    step_type: str  # question, retrieval, reasoning, generation, answer
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    confidence: float = 0.0

    def __post_init__(self):
        if not self.step_id:
            self.step_id = str(uuid.uuid4())[:8]
        if not self.timestamp:
            self.timestamp = datetime.now()


@dataclass
class RetrievedDocument:
    """检索到的文档"""

    doc_id: str
    title: str
    content: str
    source: str
    score: float
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None


@dataclass
class TraceRecord:
    """完整的溯源记录"""

    trace_id: str
    question: str
    answer: str
    steps: List[TraceStep]
    retrieved_docs: List[RetrievedDocument]
    token_usage: Optional[Dict[str, int]] = None
    latency: Optional[float] = None
    created_at: datetime = None

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "trace_id": self.trace_id,
            "question": self.question,
            "answer": self.answer,
            "steps": [
                {
                    "step_id": step.step_id,
                    "step_type": step.step_type,
                    "content": step.content,
                    "timestamp": step.timestamp.isoformat(),
                    "metadata": step.metadata,
                    "confidence": step.confidence,
                }
                for step in self.steps
            ],
            "retrieved_docs": [
                {
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "content": doc.content,
                    "source": doc.source,
                    "score": doc.score,
                    "page_number": doc.page_number,
                    "chunk_index": doc.chunk_index,
                }
                for doc in self.retrieved_docs
            ],
            "token_usage": self.token_usage,
            "latency": self.latency,
            "created_at": self.created_at.isoformat(),
        }


class TraceManager:
    """溯源管理器"""

    def __init__(self):
        self._traces: Dict[str, TraceRecord] = {}
        self._max_history = 1000  # 最大保留记录数

    def create_trace(self, question: str) -> str:
        """创建新的溯源记录"""
        trace_id = str(uuid.uuid4())
        self._traces[trace_id] = TraceRecord(
            trace_id=trace_id, question=question, answer="", steps=[], retrieved_docs=[]
        )
        return trace_id

    def add_step(
        self,
        trace_id: str,
        step_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
    ):
        """添加溯源步骤"""
        if trace_id not in self._traces:
            logger.warning(f"溯源记录不存在: {trace_id}")
            return

        step = TraceStep(
            step_id="",
            step_type=step_type,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata,
            confidence=confidence,
        )
        self._traces[trace_id].steps.append(step)

    def add_retrieved_docs(self, trace_id: str, docs: List[Dict[str, Any]]):
        """添加检索到的文档"""
        if trace_id not in self._traces:
            logger.warning(f"溯源记录不存在: {trace_id}")
            return

        retrieved_docs = []
        for doc in docs:
            retrieved_docs.append(
                RetrievedDocument(
                    doc_id=doc.get("id", ""),
                    title=doc.get("title", ""),
                    content=doc.get("content", ""),
                    source=doc.get("source", ""),
                    score=doc.get("score", 0.0),
                    page_number=doc.get("page_number"),
                    chunk_index=doc.get("chunk_index"),
                )
            )

        self._traces[trace_id].retrieved_docs = retrieved_docs

    def set_answer(
        self, trace_id: str, answer: str, token_usage: Optional[Dict[str, int]] = None, latency: Optional[float] = None
    ):
        """设置最终答案"""
        if trace_id not in self._traces:
            logger.warning(f"溯源记录不存在: {trace_id}")
            return

        self._traces[trace_id].answer = answer
        self._traces[trace_id].token_usage = token_usage
        self._traces[trace_id].latency = latency

        # 清理旧记录
        self._cleanup_old_traces()

    def get_trace(self, trace_id: str) -> Optional[TraceRecord]:
        """获取溯源记录"""
        return self._traces.get(trace_id)

    def get_trace_dict(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取溯源记录（字典格式）"""
        trace = self.get_trace(trace_id)
        if trace:
            return trace.to_dict()
        return None

    def get_recent_traces(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的溯源记录"""
        traces = list(self._traces.values())
        traces.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in traces[:limit]]

    def _cleanup_old_traces(self):
        """清理旧的溯源记录"""
        if len(self._traces) > self._max_history:
            traces = list(self._traces.values())
            traces.sort(key=lambda t: t.created_at)
            to_remove = traces[: len(traces) - self._max_history]

            for trace in to_remove:
                del self._traces[trace.trace_id]

    def generate_citation_markdown(self, trace_id: str) -> str:
        """生成引用格式的 Markdown"""
        trace = self.get_trace(trace_id)
        if not trace:
            return ""

        markdown = "## 📚 回答来源\n\n"

        if trace.retrieved_docs:
            for i, doc in enumerate(trace.retrieved_docs, 1):
                markdown += f"### 来源 {i} (相似度: {doc.score:.2f})\n\n"
                markdown += f"**标题**: {doc.title}\n\n"
                markdown += f"**来源**: {doc.source}\n\n"
                if doc.page_number:
                    markdown += f"**页码**: {doc.page_number}\n\n"
                markdown += f"**内容片段**:\n\n{doc.content[:300]}...\n\n"
        else:
            markdown += "_未找到相关参考文档_\n\n"

        return markdown.strip()

    def generate_reasoning_path(self, trace_id: str) -> str:
        """生成推理路径描述"""
        trace = self.get_trace(trace_id)
        if not trace:
            return ""

        reasoning = "## 🔍 推理过程\n\n"

        for step in trace.steps:
            step_icon = {
                "question": "❓",
                "retrieval": "🔍",
                "reasoning": "🧠",
                "generation": "✨",
                "answer": "💡",
            }.get(step.step_type, "📝")

            reasoning += f"{step_icon} **{step.step_type.capitalize()}**\n\n"
            reasoning += f"{step.content}\n\n"

            if step.confidence > 0:
                reasoning += f"置信度: {step.confidence:.2f}\n\n"

        return reasoning.strip()


# 全局溯源管理器实例
trace_manager = TraceManager()


def create_trace(question: str) -> str:
    """创建新的溯源记录"""
    return trace_manager.create_trace(question)


def add_trace_step(
    trace_id: str, step_type: str, content: str, metadata: Optional[Dict[str, Any]] = None, confidence: float = 0.0
):
    """添加溯源步骤"""
    trace_manager.add_step(trace_id, step_type, content, metadata, confidence)


def add_retrieved_docs(trace_id: str, docs: List[Dict[str, Any]]):
    """添加检索到的文档"""
    trace_manager.add_retrieved_docs(trace_id, docs)


def set_trace_answer(
    trace_id: str, answer: str, token_usage: Optional[Dict[str, int]] = None, latency: Optional[float] = None
):
    """设置最终答案"""
    trace_manager.set_answer(trace_id, answer, token_usage, latency)


def get_trace(trace_id: str) -> Optional[Dict[str, Any]]:
    """获取溯源记录"""
    return trace_manager.get_trace_dict(trace_id)


def get_recent_traces(limit: int = 10) -> List[Dict[str, Any]]:
    """获取最近的溯源记录"""
    return trace_manager.get_recent_traces(limit)


def generate_citation_markdown(trace_id: str) -> str:
    """生成引用格式的 Markdown"""
    return trace_manager.generate_citation_markdown(trace_id)


def generate_reasoning_path(trace_id: str) -> str:
    """生成推理路径描述"""
    return trace_manager.generate_reasoning_path(trace_id)
