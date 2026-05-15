"""测试向量存储"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.retrieval import get_vector_store


def main():
    print("=== 向量存储测试 ===")

    vs = get_vector_store()
    print(f"[OK] 向量存储初始化成功")

    # 清空现有数据
    vs.delete_all()
    print(f"[OK] 清空向量库")

    # 添加测试文档
    docs = [
        "苏轼是北宋著名的文学家、书法家、画家。",
        "苏轼的代表作包括《水调歌头·明月几时有》、《念奴娇·赤壁怀古》。",
        "苏轼，字子瞻，号东坡居士，四川眉山人。",
        "苏轼在诗词、散文、书法、绘画等方面都有很高的成就。",
        "苏轼一生仕途坎坷，但他的文学成就影响深远。"
    ]

    metadatas = [
        {"category": "简介", "author": "admin"},
        {"category": "作品", "author": "admin"},
        {"category": "简介", "author": "admin"},
        {"category": "成就", "author": "admin"},
        {"category": "生平", "author": "admin"}
    ]

    vs.add_documents(docs, metadatas=metadatas)
    print(f"[OK] 成功添加 {len(docs)} 个文档")

    # 测试查询
    query = "苏轼的代表作"
    print(f"\n查询: {query}")
    results = vs.similarity_search(query, k=3)

    for i, doc in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"内容: {doc['content']}")
        print(f"距离: {doc['distance']:.4f}")
        if doc.get('metadata'):
            print(f"元数据: {doc['metadata']}")

    print(f"\n总文档数: {vs.count()}")
    print(f"\n所有测试通过!")


if __name__ == "__main__":
    main()
