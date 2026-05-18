"""
Chain 模块测试
"""

import pytest
from backend.chain.rag_chain import RAGChain, RAGChainBuilder


class TestRAGChain:
    """RAGChain 测试"""

    def test_rag_chain_creation(self):
        """测试 RAG 链创建"""
        chain = RAGChain()
        assert chain is not None
        assert hasattr(chain, 'llm')
        assert hasattr(chain, 'async_llm')
        assert hasattr(chain, 'hybrid_retriever')
        assert hasattr(chain, 'use_reranking')

    def test_build_context_empty(self):
        """测试构建空上下文"""
        chain = RAGChain()
        context = chain.build_context([])
        assert context == ""

    def test_build_context_with_documents(self):
        """测试构建带文档的上下文"""
        chain = RAGChain()
        documents = [
            {"content": "苏轼是北宋文学家", "score": 0.9},
            {"content": "苏轼号东坡居士", "score": 0.8}
        ]
        context = chain.build_context(documents)
        assert "苏轼是北宋文学家" in context
        assert "苏轼号东坡居士" in context

    def test_build_prompt(self):
        """测试构建提示词"""
        chain = RAGChain()
        query = "苏轼是哪里人？"
        context = "苏轼，眉州眉山人"
        prompt = chain.build_prompt(query, context, "rag_qa")
        assert query in prompt
        assert context in prompt


class TestRAGChainBuilder:
    """RAGChainBuilder 测试"""

    def test_builder_creation(self):
        """测试构建器创建"""
        builder = RAGChainBuilder()
        assert builder is not None
        assert hasattr(builder, 'with_llm')
        assert hasattr(builder, 'with_top_k')
        assert hasattr(builder, 'build')

    def test_builder_methods(self):
        """测试构建器方法"""
        builder = RAGChainBuilder()
        result = builder.with_llm(None)
        assert result is builder
        result = builder.with_top_k(5)
        assert result is builder
