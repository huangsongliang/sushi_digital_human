"""向量存储模块 - 使用 ChromaDB 实现"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from chromadb import Client, Settings
from chromadb.api.types import QueryResult

from backend.core.config import settings
from backend.generator import get_embeddings


class VectorStore:
    """向量存储管理类"""

    def __init__(self):
        self.persist_dir = Path(settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = Client(Settings(persist_directory=str(self.persist_dir), anonymized_telemetry=False))
        self.collection = None
        self._init_collection()

    def _init_collection(self):
        """初始化或获取集合"""
        self.collection = self.client.get_or_create_collection(
            name="sushi_docs", metadata={"description": "企业文档知识库"}
        )

    def add_documents(
        self,
        texts: List[str],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ):
        """添加文档到向量库"""
        embeddings = get_embeddings()
        vectors = embeddings.embed_documents(texts)

        if not ids:
            ids = [f"doc_{i}" for i in range(len(texts))]

        self.collection.add(embeddings=vectors, documents=texts, metadatas=metadatas, ids=ids)
        return ids

    def query(self, query_text: str, n_results: int = 5, include: Optional[List[str]] = None) -> QueryResult:
        """查询相似文档"""
        embeddings = get_embeddings()
        query_vector = embeddings.embed_query(query_text)

        if include is None:
            include = ["documents", "distances", "metadatas"]

        results = self.collection.query(query_embeddings=[query_vector], n_results=n_results, include=include)
        return results

    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """简化的相似性搜索，返回文档列表"""
        results = self.query(query, n_results=k)
        docs = []
        documents = results.get("documents", [[]])
        distances = results.get("distances", [[]])
        metadatas = results.get("metadatas", [[]])

        if documents and documents[0]:
            for i, doc in enumerate(documents[0]):
                distance = distances[0][i] if distances and distances[0] else None
                metadata = metadatas[0][i] if metadatas and metadatas[0] else None
                docs.append({"content": doc, "distance": distance, "metadata": metadata})
        return docs

    def count(self) -> int:
        """获取文档数量"""
        return self.collection.count()

    def delete_all(self):
        """清空向量库"""
        self.client.delete_collection("sushi_docs")
        self._init_collection()

    def get_all_documents(self) -> List[Dict]:
        """获取所有文档"""
        try:
            all_data = self.collection.get(include=["documents", "metadatas"])

            documents = []
            for i in range(len(all_data["ids"])):
                documents.append(
                    {
                        "id": all_data["ids"][i],
                        "content": all_data["documents"][i],
                        "metadata": (all_data["metadatas"][i] if all_data["metadatas"] else None),
                    }
                )

            return documents
        except Exception as e:
            print(f"获取文档失败: {e}")
            return []


@lru_cache()
def get_vector_store() -> VectorStore:
    """获取向量存储实例（单例）"""
    return VectorStore()
