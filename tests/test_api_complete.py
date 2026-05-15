"""API 完整测试"""
import requests

# 首先添加文档到向量库
docs = [
    "苏轼是北宋著名的文学家、书法家、画家，代表作有《水调歌头·明月几时有》、《念奴娇·赤壁怀古》等。",
    "苏轼，字子瞻，号东坡居士，四川眉山人，唐宋八大家之一。",
    "苏轼的词豪放洒脱，与辛弃疾并称'苏辛'，是豪放派的代表人物。",
    "《水调歌头·明月几时有》是苏轼在中秋之夜思念弟弟苏辙时所作。",
    "《念奴娇·赤壁怀古》描写了赤壁之战的壮观景象，表达了作者对历史的感慨。"
]

print("=== 添加文档 ===")
response = requests.post("http://localhost:8000/api/docs", json=docs)
print(f"添加结果: {response.json()}")

print("\n=== 文档数量 ===")
response = requests.get("http://localhost:8000/api/docs/count")
print(f"文档数量: {response.json()}")

# 测试聊天 API
questions = [
    "苏轼的代表作有哪些",
    "苏轼是什么朝代的人",
    "《水调歌头·明月几时有》的作者是谁"
]

print("\n=== 聊天测试 ===")
for q in questions:
    print(f"\n问题: {q}")
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={"message": q, "use_rag": True}
    )
    result = response.json()
    print(f"回答: {result['answer']}")
    if result['references']:
        print(f"参考文档数: {len(result['references'])}")
