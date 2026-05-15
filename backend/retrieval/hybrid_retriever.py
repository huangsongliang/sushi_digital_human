"""混合检索模块
实现 BM25 + 向量检索 + 重排序的混合检索系统
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import os

from backend.generator import get_embeddings
from backend.retrieval import get_vector_store
from backend.utils.logger import get_logger
from backend.core.config import settings

logger = get_logger(__name__)

# 设置 Hugging Face 镜像源
hf_endpoint = os.getenv('HF_ENDPOINT', 'https://hf-mirror.com')
os.environ['HF_ENDPOINT'] = hf_endpoint
os.environ['TRANSFORMERS_OFFLINE'] = '1' if not settings.enable_reranking else '0'

logger.info(f"Hugging Face 镜像源已设置为: {hf_endpoint}")


class BM25Retriever:
    """BM25 关键词检索器"""
    
    def __init__(self):
        self.documents: List[str] = []
        self.doc_ids: List[str] = []
        self.tokenized_docs: List[List[str]] = []
        self.bm25 = None
        
    def _tokenize(self, text: str) -> List[str]:
        """简单的中文分词（基于字符）"""
        import jieba
        return list(jieba.cut(text))
    
    def add_documents(self, texts: List[str], ids: List[str]):
        """添加文档"""
        self.documents = texts
        self.doc_ids = ids
        self.tokenized_docs = [self._tokenize(doc) for doc in texts]
        
        from rank_bm25 import BM25Okapi
        self.bm25 = BM25Okapi(self.tokenized_docs)
        logger.info(f"BM25 索引已构建: {len(self.documents)} 个文档")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关文档"""
        if not self.bm25:
            logger.warning("BM25 索引未构建")
            return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "content": self.documents[idx],
                    "id": self.doc_ids[idx],
                    "score": float(scores[idx]),
                    "type": "bm25"
                })
        
        logger.info(f"BM25 检索完成: query='{query}', results={len(results)}")
        return results


class VectorRetriever:
    """向量语义检索器"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.embeddings = get_embeddings()
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关文档"""
        results = self.vector_store.similarity_search(query, k=top_k)
        
        for result in results:
            result['type'] = 'vector'
        
        logger.info(f"向量检索完成: query='{query}', results={len(results)}")
        return results


class Reranker:
    """结果重排序器"""
    
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self.model = None
        self._initialized = False
        self._enabled = settings.enable_reranking
    
    def _initialize(self):
        """延迟初始化模型"""
        if not self._initialized:
            if not self._enabled:
                logger.info("重排序已禁用")
                self._initialized = True
                return
                
            try:
                import socket
                socket.setdefaulttimeout(5)
                
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(self.model_name, max_length=512)
                self._initialized = True
                socket.setdefaulttimeout(None)
                logger.info(f"Reranker 模型已加载: {self.model_name}")
            except Exception as e:
                socket.setdefaulttimeout(None)
                logger.warning(f"Reranker 模型加载失败: {e}")
                logger.info("重排序功能将被跳过")
                self._initialized = True
    
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Dict]:
        """重排序文档"""
        if not self._enabled:
            logger.debug("重排序已禁用，返回原始顺序")
            return [{"content": doc, "rerank_score": 1.0} for doc in documents][:top_k]
        
        self._initialize()
        
        if not self.model:
            logger.debug("Reranker 模型未加载，返回原始顺序")
            return [{"content": doc, "rerank_score": 1.0} for doc in documents][:top_k]
        
        try:
            pairs = [[query, doc] for doc in documents]
            scores = self.model.predict(pairs)
            
            doc_with_scores = list(zip(documents, scores))
            doc_with_scores.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for doc, score in doc_with_scores[:top_k]:
                results.append({
                    "content": doc,
                    "rerank_score": float(score)
                })
            
            logger.info(f"重排序完成: query='{query}', reranked={len(results)}")
            return results
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return [{"content": doc, "rerank_score": 1.0} for doc in documents][:top_k]


class HybridRetriever:
    """混合检索器
    
    结合 BM25 关键词检索和向量语义检索，使用 RRF 融合后重排序
    """
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.bm25_retriever = BM25Retriever()
        self.vector_retriever = VectorRetriever(self.vector_store)
        self.reranker = Reranker()
        self._bm25_loaded = False
        self._use_reranking = settings.enable_reranking
    
    def _ensure_bm25_index(self):
        """确保 BM25 索引已构建"""
        if not self._bm25_loaded:
            documents = self.vector_store.get_all_documents()
            if documents:
                texts = [doc['content'] for doc in documents]
                ids = [doc['id'] for doc in documents]
                self.bm25_retriever.add_documents(texts, ids)
                self._bm25_loaded = True
    
    def _rrf_fusion(self, results_list: List[List[Dict]], k: int = 60) -> List[Dict]:
        """RRF (Reciprocal Rank Fusion) 融合算法"""
        doc_scores: Dict[str, Dict] = {}
        
        for results in results_list:
            for rank, result in enumerate(results, 1):
                doc_id = result.get('id', result['content'])
                
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        "content": result['content'],
                        "rrf_score": 0,
                        "details": []
                    }
                
                rrf_score = 1 / (k + rank)
                doc_scores[doc_id]['rrf_score'] += rrf_score
                doc_scores[doc_id]['details'].append({
                    'type': result.get('type', 'unknown'),
                    'score': result.get('score', result.get('distance', 0))
                })
        
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x['rrf_score'], reverse=True)
        
        for doc in sorted_docs:
            doc.pop('details', None)
        
        return sorted_docs
    
    def search(self, query: str, top_k: int = 5, use_bm25: bool = True, 
               use_vector: bool = True, use_rerank: Optional[bool] = None) -> List[Dict]:
        """混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_bm25: 是否使用 BM25 检索
            use_vector: 是否使用向量检索
            use_rerank: 是否使用重排序（None 表示使用配置设置）
        
        Returns:
            检索结果列表
        """
        if use_rerank is None:
            use_rerank = self._use_reranking
        
        results_list = []
        
        if use_bm25:
            self._ensure_bm25_index()
            bm25_results = self.bm25_retriever.search(query, top_k=top_k * 2)
            results_list.append(bm25_results)
        
        if use_vector:
            vector_results = self.vector_retriever.search(query, top_k=top_k * 2)
            results_list.append(vector_results)
        
        if not results_list:
            logger.warning("没有执行任何检索")
            return []
        
        fused_results = self._rrf_fusion(results_list)
        
        if use_rerank and fused_results:
            doc_contents = [r['content'] for r in fused_results]
            reranked = self.reranker.rerank(query, doc_contents, top_k=top_k)
            
            for original, reranked_result in zip(fused_results, reranked):
                original['rerank_score'] = reranked_result['rerank_score']
            
            fused_results = sorted(fused_results, key=lambda x: x.get('rerank_score', 0), reverse=True)
        
        logger.info(f"混合检索完成: query='{query}', results={len(fused_results[:top_k])}, "
                    f"use_bm25={use_bm25}, use_vector={use_vector}, use_rerank={use_rerank}")
        
        return fused_results[:top_k]
    
    def reload_index(self):
        """重新加载 BM25 索引"""
        self._bm25_loaded = False
        self._ensure_bm25_index()


# 全局实例
_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """获取混合检索器实例"""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
        logger.info("混合检索器已初始化")
    return _hybrid_retriever


def reload_hybrid_retriever() -> HybridRetriever:
    """重新加载混合检索器"""
    global _hybrid_retriever
    _hybrid_retriever = HybridRetriever()
    logger.info("混合检索器已重新加载")
    return _hybrid_retriever
