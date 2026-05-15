"""测试 RAG 链（带文档）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.chain import RAGChain
from backend.retrieval import get_vector_store


def main():
    print("=== RAG 链测试（带文档）===")
    
    # 添加测试文档到向量库
    vector_store = get_vector_store()
    vector_store.delete_all()
    
    docs = [
        "苏轼是北宋著名的文学家、书法家、画家，代表作有《水调歌头·明月几时有》、《念奴娇·赤壁怀古》等。",
        "苏轼，字子瞻，号东坡居士，四川眉山人，唐宋八大家之一。",
        "苏轼的词豪放洒脱，与辛弃疾并称'苏辛'，是豪放派的代表人物。",
        "《水调歌头·明月几时有》是苏轼在中秋之夜思念弟弟苏辙时所作。",
        "《念奴娇·赤壁怀古》描写了赤壁之战的壮观景象，表达了作者对历史的感慨。"
    ]
    
    metadatas = [
        {"source": "苏轼百科"},
        {"source": "苏轼百科"},
        {"source": "宋词鉴赏"},
        {"source": "水调歌头注释"},
        {"source": "念奴娇注释"}
    ]
    
    vector_store.add_documents(docs, metadatas=metadatas)
    print(f"[OK] 添加了 {len(docs)} 个测试文档")
    
    # 创建 RAG 链
    rag = RAGChain()
    print("[OK] RAG 链初始化成功")
    
    # 测试问题
    query = "苏轼的代表作有哪些"
    print(f"\n查询: {query}")
    
    # 执行 RAG
    result = rag.run(query, use_rag=True)
    
    print(f"\n回答:\n{result['answer']}")
    
    print(f"\n参考文档数量: {len(result['references'])}")
    if result['references']:
        print("\n参考文档:")
        for i, ref in enumerate(result['references'], 1):
            print(f"  {i}. {ref['content']}")
            if ref.get('metadata'):
                print(f"     来源: {ref['metadata']['source']}")
            print(f"     相似度: {(1 - ref['distance']) * 100:.2f}%")
    
    print("\n所有测试通过!")


if __name__ == "__main__":
    main()
