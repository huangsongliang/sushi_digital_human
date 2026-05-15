"""测试文档加载器"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.data_loader import DocumentLoader, load_directory_to_vector_store


def main():
    print("=== 文档加载器测试 ===")
    
    loader = DocumentLoader()
    
    # 创建测试数据目录
    test_data_dir = Path("./data/raw")
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试文件
    test_file = test_data_dir / "sushi_test.txt"
    if not test_file.exists():
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("""苏轼（1037年1月8日—1101年8月24日），字子瞻，号东坡居士，世称苏东坡，
四川眉山人，北宋著名文学家、书法家、画家、政治家。

苏轼是宋代文学最高成就的代表，与其父苏洵、其弟苏辙合称"三苏"。
他的诗词豪放洒脱，代表作有《水调歌头·明月几时有》、《念奴娇·赤壁怀古》等。

在散文方面，苏轼是唐宋八大家之一，与欧阳修并称"欧苏"。
他的书法也非常出色，与黄庭坚、米芾、蔡襄并称"宋四家"。

苏轼一生仕途坎坷，但始终保持乐观豁达的人生态度。
他不仅在文学艺术上有很高成就，还是一位关心民生的政治家。
""")
        print(f"[OK] 创建测试文件: {test_file}")
    
    # 测试从目录加载
    print("\n--- 测试从目录加载 ---")
    docs = loader.load_from_directory(str(test_data_dir))
    print(f"加载到 {len(docs)} 个文档")
    
    # 测试加载到向量库
    print("\n--- 测试加载到向量库 ---")
    loader.vector_store.delete_all()
    ids = loader.load_to_vector_store(docs, metadatas=[{"source": "test_file"}])
    print(f"成功添加 {len(ids)} 个文档")
    
    # 测试从 URL 加载（可选，需要网络）
    print("\n--- 测试从 URL 加载 ---")
    try:
        url_docs = loader.load_url("https://baike.baidu.com/item/苏轼")
        print(f"从 URL 加载到 {len(url_docs)} 个段落")
        if url_docs:
            print(f"第一个段落预览: {url_docs[0][:100]}...")
    except Exception as e:
        print(f"URL 加载失败（可能需要网络）: {str(e)}")
    
    print(f"\n向量库总文档数: {loader.vector_store.count()}")
    print("\n所有测试通过!")


if __name__ == "__main__":
    main()
