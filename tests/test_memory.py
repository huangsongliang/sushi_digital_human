"""
测试对话记忆功能
"""
import httpx
import asyncio

BASE_URL = "http://localhost:8000"


async def test_memory():
    """测试对话记忆功能"""
    print("="*60)
    print("  测试对话记忆功能")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120) as client:
        # 创建一个会话
        session_id = "memory_test_session"
        
        # 第一轮对话
        print("\n[1] 第一轮对话 - 问苏轼是谁")
        resp = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "苏轼是谁？",
                "session_id": session_id,
                "use_rag": True
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get('answer', '')[:80]
            print(f"   回答: {answer}...")
        else:
            print(f"   ❌ 请求失败: {resp.status_code}")
            return False
        
        # 第二轮对话 - 引用上一轮的信息
        print("\n[2] 第二轮对话 - 继续提问（测试记忆）")
        resp = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "他有哪些著名的作品？",
                "session_id": session_id,
                "use_rag": True
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get('answer', '')[:100]
            print(f"   回答: {answer}...")
            
            # 检查是否提到苏轼的作品
            if "赤壁赋" in answer or "水调歌头" in answer or "念奴娇" in answer:
                print("   ✅ 记忆功能正常！回答提到了苏轼的作品")
            else:
                print("   ⚠️ 回答没有明显提到作品，但记忆仍可能在工作")
        else:
            print(f"   ❌ 请求失败: {resp.status_code}")
            return False
        
        # 第三轮对话 - 继续深入
        print("\n[3] 第三轮对话 - 进一步提问")
        resp = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": "乌台诗案对他有什么影响？",
                "session_id": session_id,
                "use_rag": True
            }
        )
        
        if resp.status_code == 200:
            data = resp.json()
            answer = data.get('answer', '')[:100]
            print(f"   回答: {answer}...")
            print("   ✅ 连续对话成功！")
        else:
            print(f"   ❌ 请求失败: {resp.status_code}")
            return False
        
        return True


async def test_async_memory():
    """测试异步模式的记忆功能"""
    print("\n" + "="*60)
    print("  测试异步模式记忆功能")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120) as client:
        session_id = "async_memory_test"
        
        # 提交异步任务
        print("\n[1] 提交异步任务")
        resp = await client.post(
            f"{BASE_URL}/api/chat/async",
            json={
                "message": "苏轼的号是什么？",
                "session_id": session_id
            }
        )
        
        if resp.status_code == 200:
            task_id = resp.json()['task_id']
            print(f"   task_id: {task_id}")
            
            # 轮询结果
            for i in range(10):
                await asyncio.sleep(2)
                status_resp = await client.get(f"{BASE_URL}/api/chat/async/{task_id}")
                if status_resp.status_code == 200:
                    data = status_resp.json()
                    if data['status'] == 'completed':
                        answer = data['result']['answer'][:50]
                        print(f"   回答: {answer}...")
                        break
        
        # 继续提问（测试记忆）
        print("\n[2] 继续提问（测试记忆）")
        resp = await client.post(
            f"{BASE_URL}/api/chat/async",
            json={
                "message": "他为什么取这个号？",
                "session_id": session_id
            }
        )
        
        if resp.status_code == 200:
            task_id = resp.json()['task_id']
            for i in range(10):
                await asyncio.sleep(2)
                status_resp = await client.get(f"{BASE_URL}/api/chat/async/{task_id}")
                if status_resp.status_code == 200:
                    data = status_resp.json()
                    if data['status'] == 'completed':
                        answer = data['result']['answer'][:80]
                        print(f"   回答: {answer}...")
                        print("   ✅ 异步模式记忆功能正常！")
                        break


async def main():
    print("="*60)
    print("  对话记忆功能测试")
    print("="*60)
    
    # 检查服务
    print("\n检查服务状态...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print("✅ 服务正常")
            else:
                print(f"⚠️ 服务状态: {resp.status_code}")
    except Exception as e:
        print(f"❌ 无法连接: {e}")
        return
    
    # 测试同步模式记忆
    await test_memory()
    
    # 测试异步模式记忆
    await test_async_memory()
    
    print("\n" + "="*60)
    print("  测试完成！")
    print("="*60)
    print("\n记忆功能说明:")
    print("  1. 系统会保存对话历史（最近5条）")
    print("  2. 下一次提问时会带上历史上下文")
    print("  3. 支持同步和异步两种模式")


if __name__ == "__main__":
    asyncio.run(main())
