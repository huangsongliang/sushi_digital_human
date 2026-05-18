"""LLM生成器模块单元测试"""
from backend.generator.llm import (
    AsyncLLM,
    SimpleLLM,
    SimpleEmbeddings,
    CachedEmbeddings,
    get_llm,
    get_async_llm,
    get_embeddings,
    get_cached_embeddings
)


class TestSimpleLLM:
    """简化版LLM测试"""

    def test_simple_llm_creation(self):
        llm = SimpleLLM()
        assert llm is not None
        assert llm.model is not None


class TestAsyncLLM:
    """异步LLM测试"""

    def test_async_llm_creation(self):
        llm = AsyncLLM()
        assert llm is not None
        assert llm.model is not None

    def test_async_llm_close(self):
        llm = AsyncLLM()
        llm.close()


class TestSimpleEmbeddings:
    """简化版嵌入模型测试"""

    def test_simple_embeddings_creation(self):
        embeddings = SimpleEmbeddings()
        assert embeddings is not None
        assert embeddings.model is not None


class TestCachedEmbeddings:
    """带缓存的嵌入模型测试"""

    def test_cached_embeddings_creation(self):
        embeddings = CachedEmbeddings()
        assert embeddings is not None

    def test_cached_embeddings_disable_cache(self):
        embeddings = CachedEmbeddings()
        embeddings.disable_cache()

    def test_cached_embeddings_enable_cache(self):
        embeddings = CachedEmbeddings()
        embeddings.disable_cache()
        embeddings.enable_cache()

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
        emb1 = get_embeddings()
        emb2 = get_embeddings()
        assert emb1 is emb2

    def test_get_cached_embeddings_singleton(self):
        emb1 = get_cached_embeddings()
        emb2 = get_cached_embeddings()
        assert emb1 is emb2
