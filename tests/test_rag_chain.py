"""测试 RAG 链"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.chain import RAGChain


def main():
    print("=== RAG 链测试 ===")
    
    # 创建 RAG 链
    rag = RAGChain()
    print("[OK] RAG 链初始化成功")
    
    # 测试问题
    query = "苏轼的代表作有哪些"
    print(f"\n查询: {query}")
    
    # 执行 RAG
    result = rag.run(query, use_rag=True)
    
    print(f"\n回答: {result['answer'][:100]}...")
    print(f"\n参考文档数量: {len(result['references'])}")
    if result['references']:
        print("参考文档:")
        for i, ref in enumerate(result['references'], 1):
            print(f"  {i}. {ref['content'][:50]}... (距离: {ref['distance']:.4f})")
    
    print("\n所有测试通过!")


if __name__ == "__main__":
    main()
