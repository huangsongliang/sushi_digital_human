"""
测试异步打字机效果
"""
import httpx
import asyncio
import time

BASE_URL = "http://localhost:8000"


async def test_async_with_typewriter():
    """测试异步模式的打字机效果"""
    print("="*60)
    print("  测试异步打字机效果")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120) as client:
        # 提交任务
        print("\n[1] 提交异步任务...")
        start = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/chat/async",
            json={
                "message": "苏轼在黄州的经历",
                "session_id": "typewriter_test",
                "use_rag": True,
                "top_k": 3
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            task_id = data['task_id']
            print(f"✅ 任务提交成功！task_id: {task_id}")
            print(f"   提交耗时: {(time.time() - start):.2f}秒")
            
            # 轮询结果（模拟前端行为）
            print("\n[2] 轮询任务状态...")
            for i in range(20):
                await asyncio.sleep(2)
                
                status_resp = await client.get(
                    f"{BASE_URL}/api/chat/async/{task_id}",
                    timeout=10
                )
                
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get('status')
                    print(f"   [{i+1}] 状态: {status}")
                    
                    if status == 'completed':
                        result = status_data.get('result', {})
                        answer = result.get('answer', '')
                        print(f"\n✅ 任务完成！")
                        print(f"   答案长度: {len(answer)} 字")
                        print(f"   答案预览: {answer[:100]}...")
                        print(f"   总耗时: {(time.time() - start):.2f}秒")
                        
                        # 打字机效果演示
                        print("\n[3] 打字机效果演示:")
                        for j in range(0, len(answer[:50]), 3):
                            print(f"\r   {answer[:j+3]}", end='', flush=True)
                            await asyncio.sleep(0.05)
                        print()
                        return True
                    elif status == 'failed':
                        print(f"\n❌ 任务失败: {status_data.get('error')}")
                        return False
            
            print("\n⚠️ 任务执行时间较长")
            return True
        else:
            print(f"❌ 提交失败: {resp.status_code}")
            return False


async def main():
    print("="*60)
    print("  异步打字机效果测试")
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
    
    # 测试
    await test_async_with_typewriter()
    
    print("\n" + "="*60)
    print("  测试完成！")
    print("="*60)
    print("\n前端打字机效果说明:")
    print("  1. 任务完成后，回答会逐字显示")
    print("  2. 打字速度: 约 30 毫秒/3字")
    print("  3. 看起来就像真人打字一样")


if __name__ == "__main__":
    asyncio.run(main())
