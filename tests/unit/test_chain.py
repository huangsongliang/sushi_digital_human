"""
Chain 模块测试
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.chain.rag_chain import RAGChain, RAGChainBuilder, get_rag_chain


class TestRAGChain:
    """RAGChain 测试"""

    def test_rag_chain_creation(self):
        chain = RAGChain()
        assert chain is not None
        assert hasattr(chain, "llm")
        assert hasattr(chain, "async_llm")
        assert hasattr(chain, "hybrid_retriever")
        assert hasattr(chain, "use_reranking")

    def test_build_context_empty(self):
        chain = RAGChain()
        context = chain.build_context([])
        assert context == ""

    def test_build_context_with_documents(self):
        chain = RAGChain()
        documents = [
            {"content": "苏轼是北宋文学家", "score": 0.9},
            {"content": "苏轼号东坡居士", "score": 0.8},
        ]
        context = chain.build_context(documents)
        assert "苏轼是北宋文学家" in context
        assert "苏轼号东坡居士" in context

    def test_build_prompt(self):
        chain = RAGChain()
        query = "苏轼是哪里人？"
        context = "苏轼，眉州眉山人"
        prompt = chain.build_prompt(query, context, "rag_qa")
        assert query in prompt
        assert context in prompt

    @patch("backend.chain.rag_chain.get_llm")
    def test_generate(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            output={"choices": [{"message": {"content": "test answer"}}]}
        )
        mock_get_llm.return_value = mock_llm

        chain = RAGChain()
        chain.llm = mock_llm
        result = chain.generate("test prompt")

        assert result == "test answer"
        mock_llm.invoke.assert_called_once_with("test prompt")

    @patch("backend.chain.rag_chain.get_async_llm")
    @pytest.mark.asyncio
    async def test_async_generate(self, mock_get_async_llm):
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = MagicMock(
            output={"choices": [{"message": {"content": "async answer"}}]}
        )
        mock_get_async_llm.return_value = mock_llm

        chain = RAGChain()
        chain.async_llm = mock_llm
        result = await chain.async_generate("test prompt")

        assert result == "async answer"

    @patch("backend.chain.rag_chain.get_hybrid_retriever")
    def test_retrieve(self, mock_get_retriever):
        mock_retriever = MagicMock()
        mock_retriever.search.return_value = [{"content": "doc1", "score": 0.9}]
        mock_get_retriever.return_value = mock_retriever

        chain = RAGChain()
        chain.hybrid_retriever = mock_retriever
        results = chain.retrieve("test query", top_k=3)

        assert len(results) == 1
        assert results[0]["content"] == "doc1"

    @patch("backend.chain.rag_chain.get_hybrid_retriever")
    @pytest.mark.asyncio
    async def test_async_retrieve(self, mock_get_retriever):
        mock_retriever = AsyncMock()
        mock_retriever.async_search.return_value = [
            {"content": "async doc", "score": 0.9}
        ]
        mock_get_retriever.return_value = mock_retriever

        chain = RAGChain()
        chain.hybrid_retriever = mock_retriever
        results = await chain.async_retrieve("test query", top_k=3)

        assert len(results) == 1
        assert results[0]["content"] == "async doc"

    @patch("backend.chain.rag_chain.RAGChain.retrieve")
    @patch("backend.chain.rag_chain.RAGChain.generate")
    def test_run_with_rag(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = [{"content": "context doc"}]
        mock_generate.return_value = "answer"

        chain = RAGChain()
        result = chain.run("query", top_k=3, use_rag=True)

        assert result["answer"] == "answer"
        assert result["references"] == [{"content": "context doc"}]
        mock_retrieve.assert_called_once()
        mock_generate.assert_called_once()

    @patch("backend.chain.rag_chain.RAGChain.retrieve")
    @patch("backend.chain.rag_chain.RAGChain.generate")
    def test_run_without_rag(self, mock_generate, mock_retrieve):
        mock_generate.return_value = "answer without rag"

        chain = RAGChain()
        result = chain.run("query", top_k=3, use_rag=False)

        assert result["answer"] == "answer without rag"
        assert result["references"] == []
        mock_retrieve.assert_not_called()


class TestRAGChainBuilder:
    """RAGChainBuilder 测试"""

    def test_builder_creation(self):
        builder = RAGChainBuilder()
        assert builder is not None
        assert hasattr(builder, "with_llm")
        assert hasattr(builder, "with_top_k")
        assert hasattr(builder, "build")

    def test_builder_methods(self):
        builder = RAGChainBuilder()
        result = builder.with_llm(None)
        assert result is builder
        result = builder.with_top_k(5)
        assert result is builder

    def test_builder_build(self):
        builder = RAGChainBuilder()
        chain = builder.build()
        assert isinstance(chain, RAGChain)


class TestGetRagChain:
    """get_rag_chain 测试"""

    def test_get_rag_chain_singleton(self):
        chain1 = get_rag_chain()
        chain2 = get_rag_chain()
        assert chain1 is chain2
