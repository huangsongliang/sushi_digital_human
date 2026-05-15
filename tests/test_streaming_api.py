"""测试流式输出 API"""
import requests
import json
import sys

print("=" * 60)
print("测试流式输出 API")
print("=" * 60)

# 添加文档
print("\n1. 添加测试文档...")
docs = [
    "苏轼是北宋著名的文学家、书法家、画家，代表作有《水调歌头·明月几时有》、《念奴娇·赤壁怀古》等。",
    "苏轼，字子瞻，号东坡居士，四川眉山人，唐宋八大家之一。",
    "苏轼的词豪放洒脱，与辛弃疾并称'苏辛'，是豪放派的代表人物。",
]

response = requests.post("http://localhost:8000/api/docs", json=docs)
print(f"添加结果: {response.json()}")

# 测试流式 API
print("\n2. 测试流式聊天 API...")
print("-" * 60)

response = requests.post(
    "http://localhost:8000/api/chat/stream",
    json={
        "message": "苏轼的代表作有哪些",
        "use_rag": True,
        "top_k": 3
    },
    stream=True
)

print(f"状态码: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print("\n流式响应内容：")

full_text = ""
references = []

for line in response.iter_lines():
    if line:
        line_str = line.decode('utf-8')
        if line_str.startswith('data: '):
            data = line_str[6:]
            if data == '[DONE]':
                print("\n\n[DONE] 流式响应完成")
                break
            
            # 尝试解析 JSON
            try:
                parsed = json.loads(data)
                if parsed.get('type') == 'references':
                    references = parsed.get('data', [])
                    print(f"\n收到参考文档: {len(references)} 条")
                else:
                    print(parsed, end='', flush=True)
                    full_text += parsed
            except:
                print(data, end='', flush=True)
                full_text += data

print("\n" + "=" * 60)
print("测试完成！")
print(f"完整回答: {full_text[:100]}...")
print(f"参考文档数: {len(references)}")
print("=" * 60)
