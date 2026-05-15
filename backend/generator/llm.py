"""
LLM 依赖模块
提供 LLM 和嵌入模型的 FastAPI 依赖注入
直接使用 DashScope SDK，简洁高效
"""

from functools import lru_cache
from typing import Annotated, List, Any, AsyncGenerator

from fastapi import Depends
from dashscope import Generation
from backend.core.config import settings


class SimpleLLM:
    """简化版 LLM 封装"""

    def __init__(self):
        self.client = Generation()
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

    def invoke(self, prompt: str, **kwargs) -> Any:
        """同步调用"""
        response = self.client.call(
            model=self.model,
            prompt=prompt,
            temperature=kwargs.get('temperature', self.temperature),
            max_tokens=kwargs.get('max_tokens', self.max_tokens),
            result_format='message'
        )
        return response

    def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """异步流式调用"""
        import asyncio
        
        async def _stream():
            response = self.client.call(
                model=self.model,
                prompt=prompt,
                temperature=kwargs.get('temperature', self.temperature),
                max_tokens=kwargs.get('max_tokens', self.max_tokens),
                result_format='message',
                stream=True
            )
            
            for chunk in response:
                if chunk.status_code == 200:
                    content = chunk.output['choices'][0]['message']['content']
                    yield content
                else:
                    yield f"[错误: {chunk.message}]"
                    break
        
        return _stream()


class SimpleEmbeddings:
    """简化版嵌入模型封装"""

    def __init__(self):
        self.model = settings.embedding_model

    def embed_query(self, text: str) -> List[float]:
        """单个文本嵌入"""
        from dashscope import TextEmbedding
        response = TextEmbedding.call(
            model=self.model,
            input=text
        )
        if response.status_code == 200:
            return response.output['embeddings'][0]['embedding']
        raise Exception(f"嵌入失败: {response.message}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量文本嵌入"""
        from dashscope import TextEmbedding
        response = TextEmbedding.call(
            model=self.model,
            input=texts
        )
        if response.status_code == 200:
            return [item['embedding'] for item in response.output['embeddings']]
        raise Exception(f"嵌入失败: {response.message}")


@lru_cache()
def get_llm() -> SimpleLLM:
    """获取 LLM 实例（带缓存）"""
    return SimpleLLM()


@lru_cache()
def get_embeddings() -> SimpleEmbeddings:
    """获取嵌入模型实例（带缓存）"""
    return SimpleEmbeddings()


LLMDep = Annotated[SimpleLLM, Depends(get_llm)]
EmbeddingsDep = Annotated[SimpleEmbeddings, Depends(get_embeddings)]
