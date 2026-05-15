"""测试混合检索"""
import sys
sys.path.insert(0, 'd:/code/sushi_digital_human')

from backend.retrieval import get_hybrid_retriever, get_vector_store
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def test_hybrid_retriever():
    """测试混合检索"""
    print("=" * 60)
    print("测试混合检索系统")
    print("=" * 60)
    
    # 添加测试文档
    print("\n1. 添加测试文档...")
    vector_store = get_vector_store()
    docs = [
        "苏轼是北宋著名的文学家、书法家、画家，代表作有《水调歌头·明月几时有》、《念奴娇·赤壁怀古》等。",
        "苏轼，字子瞻，号东坡居士，四川眉山人，唐宋八大家之一。",
        "苏轼的词豪放洒脱，与辛弃疾并称'苏辛'，是豪放派的代表人物。",
        "《水调歌头·明月几时有》是苏轼在中秋之夜思念弟弟苏辙时所作。",
        "《念奴娇·赤壁怀古》描写了赤壁之战的壮观景象，表达了作者对历史的感慨。"
    ]
    ids = vector_store.add_documents(docs)
    print(f"已添加 {len(ids)} 个文档")
    
    # 获取混合检索器
    print("\n2. 获取混合检索器...")
    retriever = get_hybrid_retriever()
    print("混合检索器已就绪")
    
    # 测试查询
    test_queries = [
        "苏轼的代表作有哪些",
        "苏轼是什么朝代的人",
        "《水调歌头》的作者是谁"
    ]
    
    print("\n3. 执行混合检索测试...")
    print("-" * 60)
    
    for query in test_queries:
        print(f"\n查询: {query}")
        print("-" * 40)
        
        # 测试纯 BM25
        print("\n[BM25 检索]:")
        bm25_results = retriever.search(query, top_k=3, use_vector=False, use_rerank=False)
        for i, result in enumerate(bm25_results, 1):
            print(f"  {i}. {result.get('content', '')[:50]}... (score: {result.get('score', 0):.4f})")
        
        # 测试纯向量检索
        print("\n[向量检索]:")
        vector_results = retriever.search(query, top_k=3, use_bm25=False, use_rerank=False)
        for i, result in enumerate(vector_results, 1):
            print(f"  {i}. {result.get('content', '')[:50]}... (distance: {result.get('distance', 0):.4f})")
        
        # 测试混合检索（无重排序）
        print("\n[混合检索 (RRF融合)]:")
        hybrid_results = retriever.search(query, top_k=3, use_bm25=True, use_vector=True, use_rerank=False)
        for i, result in enumerate(hybrid_results, 1):
            print(f"  {i}. {result.get('content', '')[:50]}... (RRF score: {result.get('rrf_score', 0):.4f})")
        
        # 测试完整混合检索（含重排序）
        print("\n[完整混合检索 (RRF + 重排序)]:")
        full_results = retriever.search(query, top_k=3, use_bm25=True, use_vector=True, use_rerank=True)
        for i, result in enumerate(full_results, 1):
            print(f"  {i}. {result.get('content', '')[:50]}...")
            print(f"     RRF: {result.get('rrf_score', 0):.4f}, 重排: {result.get('rerank_score', 0):.4f}")
        
        print()
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_hybrid_retriever()
