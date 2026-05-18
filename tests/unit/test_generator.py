"""
Generator 模块测试
"""

import pytest
from backend.generator.llm import AsyncLLM, SimpleEmbeddings


class TestAsyncLLM:
    """AsyncLLM 测试"""

    def test_async_llm_creation(self):
        """测试异步 LLM 创建"""
        llm = AsyncLLM()
        assert llm is not None
        assert hasattr(llm, 'model')
        assert hasattr(llm, 'temperature')
        assert hasattr(llm, 'max_tokens')
        assert hasattr(llm, '_executor')

    def test_async_llm_attributes(self):
        """测试异步 LLM 属性"""
        llm = AsyncLLM()
        assert llm.model is not None
        assert isinstance(llm.temperature, float)
        assert isinstance(llm.max_tokens, int)
        assert llm._executor is not None


class TestSimpleEmbeddings:
    """SimpleEmbeddings 测试"""

    def test_simple_embeddings_creation(self):
        """测试简单嵌入创建"""
        embeddings = SimpleEmbeddings()
        assert embeddings is not None
        assert hasattr(embeddings, 'model')

    def test_simple_embeddings_attributes(self):
        """测试简单嵌入属性"""
        embeddings = SimpleEmbeddings()
        assert embeddings.model is not None
