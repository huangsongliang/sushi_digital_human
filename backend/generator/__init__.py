"""
Generator 模块 - LLM 配置
"""

from backend.generator.llm import (
    SimpleLLM,
    SimpleEmbeddings,
    get_llm,
    get_embeddings,
    LLMDep,
    EmbeddingsDep
)

__all__ = [
    "SimpleLLM",
    "SimpleEmbeddings",
    "get_llm",
    "get_embeddings",
    "LLMDep",
    "EmbeddingsDep"
]
