"""
添加测试文档到知识库
"""
import httpx

BASE_URL = "http://localhost:8001"

documents = [
    """苏轼（1037年－1101年），字子瞻，号东坡居士，四川眉山人，北宋著名文学家、书画家。他是宋代文学最高成就的代表之一，与父苏洵、弟苏辙合称“三苏”。苏轼在诗词文赋书画各方面都有很高造诣，其诗题材广阔，清新豪健，善用夸张比喻，独具风格，与黄庭坚并称“苏黄”；其词开豪放一派，与辛弃疾并称“苏辛”。""",
    """《水调歌头·明月几时有》是苏轼的代表作之一，作于宋神宗熙宁九年（1076年）中秋。当时苏轼在密州（今山东诸城）任知州，与弟弟苏辙分别已有七年。这首词以月起兴，围绕中秋明月展开想象和思考，把人世间的悲欢离合之情纳入对宇宙人生的哲理性追寻之中，反映了作者复杂而又矛盾的思想感情，又表现出作者热爱生活与积极向上的乐观精神。""",
    """乌台诗案是北宋著名的文字狱，发生于元丰二年（1079年）。苏轼因被弹劾所作诗文讥讽朝政而被捕入狱，经多方营救才得以免死，被贬为黄州团练副使。这一事件对苏轼影响深远，是他人生的重要转折点。在黄州期间，苏轼写下了《赤壁赋》《念奴娇·赤壁怀古》等千古名篇。""",
]

print("="*50)
print("  添加测试文档到知识库")
print("="*50)
print(f"\n文档数量: {len(documents)}")

try:
    resp = httpx.post(
        f"{BASE_URL}/api/docs/add",
        json={"documents": documents},
        timeout=30
    )
    print(f"\n状态码: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ 添加成功！count: {data.get('count')}")
        print(f"IDs: {data.get('ids')}")
    else:
        print(f"⚠️ 响应: {resp.text}")
except Exception as e:
    print(f"\n❌ 出错: {e}")
    import traceback
    traceback.print_exc()
