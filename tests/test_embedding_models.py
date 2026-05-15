"""测试 DashScope 嵌入模型"""
import dashscope

dashscope.api_key = "your-dashscope-api-key"

# 测试不同的嵌入模型
models = [
    "text-embedding-v2",
    "text-embedding-v1",
    "text-embedding-v3",
    "text-embedding-async-v2",
]

for model in models:
    try:
        from dashscope import TextEmbedding
        response = TextEmbedding.call(
            model=model,
            input="测试文本"
        )
        if response.status_code == 200:
            print(f"[OK] {model}: 成功，维度: {len(response.output['embeddings'][0]['embedding'])}")
        else:
            print(f"[FAIL] {model}: {response.message}")
    except Exception as e:
        print(f"[ERROR] {model}: {str(e)}")
