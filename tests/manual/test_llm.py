"""测试 LLM 配置"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.generator import get_llm, get_embeddings
from backend.core.config import settings


def main():
    print("=== LLM 配置测试 ===")
    print(f"模型: {settings.llm_model}")
    print(f"嵌入模型: {settings.embedding_model}")

    # 测试 LLM
    llm = get_llm()
    print(f"\n[OK] LLM 初始化成功: {llm.model}")

    # 测试嵌入
    embeddings = get_embeddings()
    print(f"[OK] 嵌入模型初始化成功: {embeddings.model}")

    # 测试调用
    print("\n测试 LLM 调用...")
    response = llm.invoke("用一句话介绍苏轼")
    if response.status_code == 200:
        content = response.output["choices"][0]["message"]["content"]
        print(f"[OK] LLM 响应: {content[:50]}...")
    else:
        print(f"[FAIL] LLM 调用失败: {response.message}")

    # 测试嵌入
    print("\n测试嵌入模型...")
    vector = embeddings.embed_query("苏轼的诗词")
    print(f"[OK] 嵌入向量维度: {len(vector)}")

    print("\n所有测试通过!")


if __name__ == "__main__":
    main()
