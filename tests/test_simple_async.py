"""
超简单验证测试（端口 8001）
"""
import httpx
import time
import asyncio

BASE_URL = "http://localhost:8001"


async def main():
    print("="*50)
    print("  异步功能快速验证")
    print("="*50)
    
    # 1. 检查健康
    print("\n[1] 检查服务健康...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print("✅ 服务正常运行！")
            else:
                print(f"⚠️ 状态码: {resp.status_code}")
                print(f"响应: {resp.text}")
    except Exception as e:
        print(f"❌ 无法连接: {e}")
        print("\n提示：确保服务正在端口 8001 运行")
        return
    
    # 2. 测试异步提交
    print("\n[2] 测试异步聊天...")
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # 提交任务
            print("\n  ① 提交任务...")
            start_submit = time.time()
            resp = await client.post(
                f"{BASE_URL}/api/chat/async",
                json={
                    "message": "苏轼是谁？",
                    "session_id": "quick_test",
                    "use_rag": True,
                    "top_k": 3
                },
                timeout=10
            )
            submit_time = time.time() - start_submit
            
            if resp.status_code == 200:
                data = resp.json()
                task_id = data['task_id']
                print(f"  ✅ 提交成功！task_id: {task_id}")
                print(f"  ⏱️  提交耗时: {submit_time:.2f}秒（非常快！）")
                
                # 轮询 5 次
                print("\n  ② 轮询结果...")
                for i in range(10):
                    await asyncio.sleep(3)
                    
                    status_resp = await client.get(
                        f"{BASE_URL}/api/chat/async/{task_id}",
                        timeout=10
                    )
                    
                    if status_resp.status_code == 200:
                        status_data = status_resp.json()
                        status = status_data.get('status')
                        print(f"     [{i+1}] 状态: {status}")
                        
                        if status == 'completed':
                            result = status_data.get('result', {})
                            answer = result.get('answer', '')
                            print("\n  ✅ 任务完成！")
                            print(f"  📝 答案: {answer[:80]}...")
                            return
                        elif status == 'failed':
                            print(f"\n  ❌ 失败: {status_data.get('error')}")
                            return
                print("\n  ⚠️  任务执行中...")
            else:
                print(f"  ❌ 提交失败: {resp.status_code}")
                print(f"  响应: {resp.text}")
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
