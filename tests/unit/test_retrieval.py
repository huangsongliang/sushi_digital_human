"""
Retrieval 模块测试
"""

import pytest
from backend.retrieval.hybrid_retriever import BM25Retriever, VectorRetriever


class TestBM25Retriever:
    """BM25Retriever 测试"""

    def test_bm25_creation(self):
        """测试 BM25 创建"""
        retriever = BM25Retriever()
        assert retriever.documents == []
        assert retriever.doc_ids == []
        assert retriever.tokenized_docs == []
        assert retriever.bm25 is None

    def test_bm25_add_documents(self):
        """测试添加文档"""
        retriever = BM25Retriever()
        texts = ["苏轼是北宋著名的文学家", "李白是唐代浪漫主义诗人"]
        ids = ["doc1", "doc2"]
        retriever.add_documents(texts, ids)
        assert len(retriever.documents) == 2
        assert len(retriever.doc_ids) == 2
        assert len(retriever.tokenized_docs) == 2
        assert retriever.bm25 is not None

    def test_bm25_search_no_index(self):
        """测试未构建索引时的搜索"""
        retriever = BM25Retriever()
        results = retriever.search("测试查询")
        assert results == []

    def test_bm25_search_with_index(self):
        """测试构建索引后的搜索"""
        retriever = BM25Retriever()
        texts = [
            "苏轼是北宋著名的文学家",
            "苏轼号东坡居士",
            "李白是唐代诗人"
        ]
        ids = ["doc1", "doc2", "doc3"]
        retriever.add_documents(texts, ids)
        results = retriever.search("苏轼", top_k=2)
        assert len(results) <= 2
        assert all(r["type"] == "bm25" for r in results)

    def test_bm25_tokenize(self):
        """测试分词功能"""
        retriever = BM25Retriever()
        tokens = retriever._tokenize("苏轼是北宋人")
        assert isinstance(tokens, list)
        assert len(tokens) > 0


class TestVectorRetriever:
    """VectorRetriever 测试"""

    def test_vector_retriever_creation(self):
        """测试 VectorRetriever 创建（需要 mock）"""
        # 由于 VectorRetriever 需要真实的 vector_store，这里只测试结构
        pass  # 实际测试需要 mock
