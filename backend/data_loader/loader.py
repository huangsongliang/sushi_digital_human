"""文档加载器模块
支持从多种数据源导入文档到向量库
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.retrieval import get_vector_store


class DocumentLoader:
    """文档加载器"""

    def __init__(self):
        self.vector_store = get_vector_store()

    def load_from_file(self, file_path: str) -> List[str]:
        """从文件加载文档"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = path.suffix.lower()
        
        if ext == ".txt":
            return self._load_txt(path)
        elif ext == ".md":
            return self._load_markdown(path)
        elif ext == ".json":
            return self._load_json(path)
        elif ext == ".csv":
            return self._load_csv(path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _load_txt(self, path: Path) -> List[str]:
        """加载 TXT 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [content]

    def _load_markdown(self, path: Path) -> List[str]:
        """加载 Markdown 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return [content]

    def _load_json(self, path: Path) -> List[str]:
        """加载 JSON 文件"""
        import json
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return [str(item) for item in data]
        elif isinstance(data, dict):
            return [json.dumps(data, ensure_ascii=False)]
        return [str(data)]

    def _load_csv(self, path: Path) -> List[str]:
        """加载 CSV 文件"""
        import csv
        rows = []
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(str(row))
        return rows

    def load_from_directory(self, dir_path: str, pattern: str = "*.txt") -> List[str]:
        """从目录批量加载文件"""
        dir_path = Path(dir_path)
        documents = []
        
        for file_path in dir_path.glob(pattern):
            try:
                docs = self.load_from_file(str(file_path))
                documents.extend(docs)
                print(f"[OK] 加载文件: {file_path}")
            except Exception as e:
                print(f"[FAIL] 加载文件 {file_path} 失败: {str(e)}")
        
        return documents

    def load_url(self, url: str) -> List[str]:
        """从 URL 加载网页内容"""
        import requests
        from bs4 import BeautifulSoup
        
        try:
            response = requests.get(url, timeout=30)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(strip=True)
            
            # 按段落分割
            paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 20]
            return paragraphs
        except Exception as e:
            print(f"加载 URL 失败: {str(e)}")
            return []

    def load_to_vector_store(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """加载文档到向量库"""
        if not documents:
            print("没有文档可加载")
            return []
        
        if metadatas is None:
            metadatas = [{"source": "manual"}] * len(documents)
        
        ids = self.vector_store.add_documents(documents, metadatas=metadatas)
        print(f"成功加载 {len(documents)} 个文档到向量库")
        return ids

    def load_from_jsonl(self, file_path: str) -> List[str]:
        """加载 JSONL 文件"""
        documents = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    documents.append(line)
        return documents


# 便捷函数
def load_documents_to_vector_store(documents: List[str]) -> List[str]:
    """便捷函数：加载文档到向量库"""
    loader = DocumentLoader()
    return loader.load_to_vector_store(documents)


def load_directory_to_vector_store(dir_path: str, pattern: str = "*.txt") -> List[str]:
    """便捷函数：从目录加载到向量库"""
    loader = DocumentLoader()
    docs = loader.load_from_directory(dir_path, pattern)
    return loader.load_to_vector_store(docs)
