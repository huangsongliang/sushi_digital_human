"""
快速验证：测试任务管理器在多 worker 下的 Redis 存储
"""
import asyncio
import httpx
import time
import random
from typing import List

BASE_URL = "http://localhost:8000"

# 测试问题
QUERIES = [
    "苏轼是谁？",
    "水调歌头的主要内容是什么？",
    "乌台诗案是怎么回事？",
    "苏轼在黄州的经历",
    "苏轼与苏辙的关系",
    "西湖苏堤是谁修的？",
]


async def test_single_async():
    """测试单个异步任务"""
    print("\n" + "="*60)
    print(" 测试 1: 单个异步任务")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=60) as client:
        # 1. 提交任务
        print("\n1. 提交任务...")
        start = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/chat/async",
            json={
                "message": random.choice(QUERIES),
                "session_id": "test_single",
                "use_rag": True,
                "top_k": 3
            },
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            task_id = data['task_id']
            submit_time = time.time() - start
            print(f"   ✅ 任务提交成功，task_id: {task_id}")
            print(f"   ⏱️  提交耗时: {submit_time:.2f}秒（用户无感知！）")
            
            # 2. 轮询结果
            print("\n2. 轮询结果...")
            for i in range(40):  # 最多等 2 分钟
                await asyncio.sleep(3)
                
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
                        print(f"\n   ✅ 任务完成！")
                        print(f"   📝 答案: {answer[:100]}...")
                        total_time = time.time() - start
                        print(f"   ⏱️  总耗时: {total_time:.2f}秒")
                        return True
                    elif status == 'failed':
                        error = status_data.get('error', '未知错误')
                        print(f"\n   ❌ 任务失败: {error}")
                        return False
        else:
            print(f"   ❌ 提交失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False


async def test_concurrent_async():
    """测试并发异步任务"""
    print("\n" + "="*60)
    print(" 测试 2: 并发异步任务 (5 个)")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=120) as client:
        # 1. 同时提交 5 个任务
        print("\n1. 同时提交 5 个任务...")
        start = time.time()
        task_ids = []
        
        submit_tasks = []
        for i in range(5):
            query = QUERIES[i % len(QUERIES)]
            submit_tasks.append(client.post(
                f"{BASE_URL}/api/chat/async",
                json={
                    "message": query,
                    "session_id": f"test_concurrent_{i}",
                    "use_rag": True,
                    "top_k": 3
                },
                timeout=10
            ))
        
        responses = await asyncio.gather(*submit_tasks)
        
        for i, resp in enumerate(responses):
            if resp.status_code == 200:
                data = resp.json()
                task_ids.append(data['task_id'])
                print(f"   [{i+1}] ✅ task_id: {data['task_id']}")
            else:
                print(f"   [{i+1}] ❌ 提交失败")
        
        submit_time = time.time() - start
        print(f"\n   ⏱️  全部提交耗时: {submit_time:.2f}秒")
        
        if not task_ids:
            return False
        
        # 2. 轮询所有任务
        print("\n2. 轮询任务结果...")
        completed = 0
        failed = 0
        
        for round in range(60):  # 最多等 3 分钟
            await asyncio.sleep(3)
            
            for i, task_id in enumerate(task_ids):
                if task_id is None:
                    continue
                
                status_resp = await client.get(
                    f"{BASE_URL}/api/chat/async/{task_id}",
                    timeout=10
                )
                
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get('status')
                    
                    if status == 'completed':
                        print(f"   [{i+1}] ✅ 完成")
                        task_ids[i] = None
                        completed += 1
                    elif status == 'failed':
                        print(f"   [{i+1}] ❌ 失败")
                        task_ids[i] = None
                        failed += 1
            
            if all(t is None for t in task_ids):
                print("\n   所有任务完成！")
                break
        
        total_time = time.time() - start
        print(f"\n   📊 统计:")
        print(f"   - 完成: {completed}")
        print(f"   - 失败: {failed}")
        print(f"   - 总耗时: {total_time:.2f}秒")
        
        if completed > 0:
            return True
        return False


async def main():
    print("="*60)
    print("  异步任务功能验证")
    print("="*60)
    
    # 先检查服务是否运行
    print("\n检查服务状态...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            health_resp = await client.get(f"{BASE_URL}/health")
            if health_resp.status_code == 200:
                print("✅ 服务运行正常！")
            else:
                print("⚠️  服务可能有问题")
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print("\n请先运行: uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2")
        return
    
    # 测试 1
    test1_ok = await test_single_async()
    
    # 测试 2
    test2_ok = await test_concurrent_async()
    
    # 总结
    print("\n" + "="*60)
    print("  总结")
    print("="*60)
    if test1_ok:
        print("✅ 单个异步任务 - 通过")
    else:
        print("❌ 单个异步任务 - 失败")
    
    if test2_ok:
        print("✅ 并发异步任务 - 通过")
    else:
        print("❌ 并发异步任务 - 失败")
    
    print("\n提示：如果要测试多进程下的 Redis 共享存储，")
    print("请设置环境变量: USE_REDIS_STORAGE=true")
    print("并确保 Redis 正在运行")


if __name__ == "__main__":
    asyncio.run(main())
