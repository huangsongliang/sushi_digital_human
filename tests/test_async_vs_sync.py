"""对比测试同步和异步API的性能"""
import httpx
import time
import asyncio
import statistics
from typing import List, Dict

BASE_URL = "http://localhost:8000"
NUM_REQUESTS = 15
CONCURRENT = 10

TEST_QUERIES = [
    "苏轼是谁？",
    "水调歌头的主要内容",
    "乌台诗案是什么事件",
    "苏轼在黄州的经历",
    "苏轼与苏辙的关系"
]


async def test_sync_api():
    """测试同步API"""
    print("=== 测试同步API ===")
    
    async with httpx.AsyncClient(timeout=60) as client:
        start = time.time()
        tasks = []
        
        for i in range(NUM_REQUESTS):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            task = client.post(
                f"{BASE_URL}/api/chat",
                json={
                    "message": query,
                    "session_id": f"sync_test_{i}",
                    "use_rag": True,
                    "top_k": 3
                }
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        latencies = []
        errors = []
        
        for i, resp in enumerate(responses):
            if isinstance(resp, Exception):
                errors.append(str(resp))
            elif resp.status_code == 200:
                success_count += 1
                latencies.append(resp.elapsed.total_seconds())
        
        total_time = time.time() - start
        
        print(f"总请求数: {NUM_REQUESTS}")
        print(f"成功数: {success_count}")
        print(f"成功率: {success_count/NUM_REQUESTS*100:.1f}%")
        if latencies:
            print(f"平均响应时间: {statistics.mean(latencies):.2f}秒")
            print(f"中位响应时间: {statistics.median(latencies):.2f}秒")
            print(f"最慢响应: {max(latencies):.2f}秒")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"吞吐量: {success_count/total_time:.2f} req/sec")
        if errors:
            print(f"错误: {len(errors)} 个 - {errors[:3]}")
        
        return {
            "success": success_count,
            "total": NUM_REQUESTS,
            "latencies": latencies,
            "total_time": total_time
        }


async def test_async_api():
    """测试异步API（提交+轮询模式）"""
    print("\n=== 测试异步API ===")
    
    async with httpx.AsyncClient(timeout=60) as client:
        start = time.time()
        
        # 1. 快速提交所有任务
        task_ids = []
        submit_errors = []
        
        for i in range(NUM_REQUESTS):
            query = TEST_QUERIES[i % len(TEST_QUERIES)]
            try:
                resp = await client.post(
                    f"{BASE_URL}/api/chat/async",
                    json={
                        "message": query,
                        "session_id": f"async_test_{i}",
                        "use_rag": True,
                        "top_k": 3
                    },
                    timeout=10
                )
                if resp.status_code == 200:
                    task_ids.append(resp.json()['task_id'])
                else:
                    submit_errors.append(f"{resp.status_code}")
            except Exception as e:
                submit_errors.append(str(e))
        
        submit_time = time.time() - start
        print(f"任务提交完成，耗时: {submit_time:.2f}秒")
        print(f"成功提交: {len(task_ids)}, 失败: {len(submit_errors)}")
        
        # 2. 轮询等待所有任务完成
        completed = {}
        poll_start = time.time()
        max_poll_time = 120  # 最多等2分钟
        
        while len(completed) < len(task_ids) and (time.time() - poll_start) < max_poll_time:
            to_check = [tid for tid in task_ids if tid not in completed]
            
            for tid in to_check:
                try:
                    resp = await client.get(f"{BASE_URL}/api/chat/async/{tid}", timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        status = data.get('status')
                        if status == 'completed' or status == 'failed':
                            completed[tid] = data
                except Exception as e:
                    pass
            
            if len(completed) < len(task_ids):
                await asyncio.sleep(2)
        
        # 统计结果
        success_count = 0
        task_times = []
        errors = []
        
        for tid, data in completed.items():
            if data.get('status') == 'completed':
                success_count += 1
            else:
                errors.append(data.get('error', 'unknown'))
        
        total_time = time.time() - start
        
        print(f"\n总任务数: {len(task_ids)}")
        print(f"完成数: {len(completed)}")
        print(f"成功数: {success_count}")
        print(f"成功率: {success_count/len(task_ids)*100:.1f}%")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"吞吐量: {success_count/total_time:.2f} req/sec")
        if errors:
            print(f"错误: {len(errors)} 个")
        
        return {
            "success": success_count,
            "total": len(task_ids),
            "total_time": total_time
        }


async def main():
    print("="*60)
    print("  同步API vs 异步API 性能对比")
    print("="*60)
    
    print(f"\n测试配置:")
    print(f"  - 请求数: {NUM_REQUESTS}")
    print(f"  - 并发数: {CONCURRENT}")
    
    await asyncio.sleep(2)
    
    # 1. 测试同步API
    sync_result = await test_sync_api()
    
    await asyncio.sleep(2)
    
    # 2. 测试异步API
    async_result = await test_async_api()
    
    # 3. 总结
    print("\n" + "="*60)
    print("  总结")
    print("="*60)
    
    sync_tps = sync_result['success'] / sync_result['total_time']
    async_tps = async_result['success'] / async_result['total_time']
    
    print(f"\n同步API:")
    print(f"  成功率: {sync_result['success']/sync_result['total']*100:.1f}%")
    print(f"  吞吐量: {sync_tps:.2f} req/sec")
    
    print(f"\n异步API:")
    print(f"  成功率: {async_result['success']/async_result['total']*100:.1f}%")
    print(f"  吞吐量: {async_tps:.2f} req/sec")
    
    print(f"\n对比:")
    if async_tps > sync_tps:
        print(f"  🚀 异步API快 {(async_tps/sync_tps - 1)*100:.0f}%")
    else:
        print(f"  性能相近或相当")
    
    print("\n✅ 异步API的主要优势:")
    print("  - 用户体验更好（请求立即返回，不阻塞UI）")
    print("  - 可以显示任务进度")
    print("  - 系统可以更好地控制并发（排队机制）")


if __name__ == "__main__":
    asyncio.run(main())
