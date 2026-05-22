"""RAG 链模块
实现完整的 RAG 流程：文档获取 -> 分块 -> 检索 -> 提示词构建 -> LLM 调用
支持同步和流式两种调用方式
使用混合检索器（BM25 + 向量 + RRF + 重排序）提升检索质量
"""

from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio

from backend.generator import get_llm, get_async_llm
from backend.retrieval import get_hybrid_retriever
from backend.prompt import default_prompts
from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.performance import timed_operation
from backend.chain.rag_cache import get_rag_cache

logger = get_logger(__name__)


class RAGChain:
    """RAG 链实现 - 使用混合检索"""

    def __init__(self):
        self.llm = get_llm()
        self.async_llm = get_async_llm()
        self.hybrid_retriever = get_hybrid_retriever()
        self.use_reranking = settings.enable_reranking

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索相关文档（使用混合检索）"""
        logger.info(f"开始混合检索 - 查询: {query}")

        with timed_operation("hybrid_retrieval"):
            results = self.hybrid_retriever.search(
                query,
                top_k=top_k,
                use_bm25=True,
                use_vector=True,
                use_rerank=self.use_reranking,
            )

        logger.info(f"混合检索完成 - 获取到 {len(results)} 条结果")
        return results

    async def async_retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """异步检索相关文档（使用混合检索，带缓存）"""
        logger.info(f"开始异步混合检索 - 查询: {query}")

        # 先尝试从缓存获取
        rag_cache = get_rag_cache()
        cached_results = await rag_cache.get(
            query=query,
            top_k=top_k,
            use_bm25=True,
            use_vector=True,
            use_rerank=self.use_reranking
        )

        if cached_results is not None:
            logger.info(f"使用缓存结果 - 查询: {query[:50]}...")
            return cached_results

        # 缓存未命中，执行实际检索
        with timed_operation("async_hybrid_retrieval"):
            results = await self.hybrid_retriever.async_search(
                query,
                top_k=top_k,
                use_bm25=True,
                use_vector=True,
                use_rerank=self.use_reranking,
            )

        # 保存到缓存
        await rag_cache.set(
            query=query,
            top_k=top_k,
            use_bm25=True,
            use_vector=True,
            use_rerank=self.use_reranking,
            results=results
        )

        logger.info(f"异步混合检索完成 - 获取到 {len(results)} 条结果")
        return results

    def build_context(self, documents: List[Dict]) -> str:
        """构建上下文文本"""
        if not documents:
            return ""
        return "\n\n".join([doc["content"] for doc in documents])

    def build_prompt(self, query: str, context: str, prompt_type: str = "rag_qa") -> str:
        """构建提示词"""
        return default_prompts.format(prompt_type, context=context, question=query)

    def generate(self, prompt: str) -> str:
        """调用 LLM 生成回答（同步）"""
        response = self.llm.invoke(prompt)
        try:
            return response.output["choices"][0]["message"]["content"]
        except (KeyError, IndexError, AttributeError) as e:
            logger.error(f"解析 LLM 同步响应失败: {e}")
            return "抱歉，生成回答时出现错误，请稍后重试。"

    async def async_generate(self, prompt: str) -> str:
        """异步调用 LLM 生成回答"""
        response = await self.async_llm.invoke(prompt)
        try:
            return response.output["choices"][0]["message"]["content"]
        except (KeyError, IndexError, AttributeError) as e:
            logger.error(f"解析 LLM 异步响应失败: {e}")
            return "抱歉，生成回答时出现错误，请稍后重试。"

    def run(self, query: str, top_k: int = 3, use_rag: bool = True) -> Dict[str, Any]:
        """执行完整的 RAG 流程"""
        # 1. 检索阶段
        documents = []
        context = ""

        if use_rag:
            documents = self.retrieve(query, top_k=top_k)
            context = self.build_context(documents)

        # 2. 构建提示词
        prompt = self.build_prompt(query, context)

        # 3. 生成回答
        answer = self.generate(prompt)

        # 4. 整理结果
        return {
            "answer": answer,
            "query": query,
            "references": documents,
            "context": context,
            "prompt": prompt,
        }

    async def async_run(self, query: str, top_k: int = 3, use_rag: bool = True, history: str = "") -> Dict[str, Any]:
        """异步执行完整的 RAG 流程（使用线程池优化）"""
        # 1. 检索阶段（异步，带缓存）
        documents = []
        context = ""

        if use_rag:
            documents = await self.async_retrieve(query, top_k=top_k)
            context = self.build_context(documents)

        # 2. 构建提示词（支持历史对话）
        if history:
            prompt = default_prompts.format("multi_turn", history=history, question=query, context=context)
        else:
            prompt = self.build_prompt(query, context)

        # 3. 异步生成回答
        answer = await self.async_generate(prompt)

        # 4. 整理结果
        return {
            "answer": answer,
            "query": query,
            "references": documents,
            "context": context,
            "prompt": prompt,
        }

    async def stream_run(
        self, query: str, top_k: int = 3, use_rag: bool = True, history: str = ""
    ) -> AsyncGenerator[str, None]:
        """流式执行 RAG 流程（使用异步检索，带缓存）"""
        # 1. 检索阶段（异步，带缓存）
        documents = []
        context = ""

        if use_rag:
            documents = await self.async_retrieve(query, top_k=top_k)
            context = self.build_context(documents)

        # 2. 构建提示词（支持历史对话）
        if history:
            prompt = default_prompts.format("multi_turn", history=history, question=query, context=context)
        else:
            prompt = self.build_prompt(query, context)

        # 3. 流式生成（使用异步 LLM）
        async for chunk in self.async_llm.stream(prompt):
            yield chunk

    def get_references(self, query: str, top_k: int = 3) -> List[Dict]:
        """获取参考文档（用于流式调用时）"""
        return self.retrieve(query, top_k=top_k)


class RAGChainBuilder:
    """RAG 链构建器（可选扩展）"""

    def __init__(self):
        self._llm = None
        self._vector_store = None
        self._prompt_manager = None
        self._top_k = 3

    def with_llm(self, llm):
        """设置 LLM"""
        self._llm = llm
        return self

    def with_vector_store(self, vector_store):
        """设置向量存储"""
        self._vector_store = vector_store
        return self

    def with_prompt_manager(self, prompt_manager):
        """设置提示词管理器"""
        self._prompt_manager = prompt_manager
        return self

    def with_top_k(self, top_k):
        """设置检索数量"""
        self._top_k = top_k
        return self

    def build(self) -> RAGChain:
        """构建 RAG 链"""
        chain = RAGChain()
        if self._llm:
            chain.llm = self._llm
        if self._vector_store:
            chain.hybrid_retriever.vector_store = self._vector_store
        if self._top_k:
            # top_k 在每次调用 run/stream_run 时通过参数控制，这里仅记录默认值
            pass
        return chain


# 全局 RAG 链实例
rag_chain = RAGChain()


def get_rag_chain() -> RAGChain:
    """获取 RAG 链实例"""
    return rag_chain
