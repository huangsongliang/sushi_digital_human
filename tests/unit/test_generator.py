"""
Generator 模块测试
"""

import pytest
from unittest.mock import MagicMock, patch
from backend.generator.llm import AsyncLLM, SimpleLLM, SimpleEmbeddings, CachedEmbeddings, get_llm, get_async_llm, get_embeddings, get_cached_embeddings


class TestAsyncLLM:
    """AsyncLLM 测试"""

    def test_async_llm_creation(self):
        llm = AsyncLLM()
        assert llm is not None
        assert hasattr(llm, 'model')
        assert hasattr(llm, 'temperature')
        assert hasattr(llm, 'max_tokens')
        assert hasattr(llm, '_executor')

    def test_async_llm_attributes(self):
        llm = AsyncLLM()
        assert llm.model is not None
        assert isinstance(llm.temperature, float)
        assert isinstance(llm.max_tokens, int)
        assert llm._executor is not None

    def test_async_llm_close(self):
        llm = AsyncLLM()
        llm.close()


class TestSimpleLLM:
    """SimpleLLM 测试"""

    def test_simple_llm_creation(self):
        llm = SimpleLLM()
        assert llm is not None
        assert hasattr(llm, 'client')
        assert hasattr(llm, 'model')
        assert hasattr(llm, 'temperature')
        assert hasattr(llm, 'max_tokens')


class TestSimpleEmbeddings:
    """SimpleEmbeddings 测试"""

    def test_simple_embeddings_creation(self):
        embeddings = SimpleEmbeddings()
        assert embeddings is not None
        assert hasattr(embeddings, 'model')

    def test_simple_embeddings_attributes(self):
        embeddings = SimpleEmbeddings()
        assert embeddings.model is not None


class TestCachedEmbeddings:
    """CachedEmbeddings 测试"""

    def test_cached_embeddings_creation(self):
        embeddings = CachedEmbeddings()
        assert embeddings is not None
        assert embeddings._cache_enabled is True
        assert embeddings._executor is not None

    def test_cached_embeddings_disable_cache(self):
        embeddings = CachedEmbeddings()
        embeddings.disable_cache()
        assert embeddings._cache_enabled is False

    def test_cached_embeddings_enable_cache(self):
        embeddings = CachedEmbeddings()
        embeddings.disable_cache()
        embeddings.enable_cache()
        assert embeddings._cache_enabled is True

    def test_cached_embeddings_close(self):
        embeddings = CachedEmbeddings()
        embeddings.close()


class TestSingletonFunctions:
    """单例函数测试"""

    def test_get_llm_singleton(self):
        llm1 = get_llm()
        llm2 = get_llm()
        assert llm1 is llm2

    def test_get_async_llm_singleton(self):
        llm1 = get_async_llm()
        llm2 = get_async_llm()
        assert llm1 is llm2

    def test_get_embeddings_singleton(self):
        embeddings1 = get_embeddings()
        embeddings2 = get_embeddings()
        assert embeddings1 is embeddings2

    def test_get_cached_embeddings_singleton(self):
        embeddings1 = get_cached_embeddings()
        embeddings2 = get_cached_embeddings()
        assert embeddings1 is embeddings2