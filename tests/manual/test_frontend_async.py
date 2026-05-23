"""
前端异步功能测试脚本
"""

import httpx
import asyncio
import time
import random

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:5173"


async def test_async_api():
    """测试异步API"""
    print("=" * 60)
    print("  测试异步 API")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=120) as client:
        # 1. 提交任务
        print("\n[1] 提交异步任务...")
        start = time.time()
        resp = await client.post(
            f"{BASE_URL}/api/chat/async",
            json={
                "message": "苏轼是谁？",
                "session_id": "test_frontend",
                "use_rag": True,
                "top_k": 3,
            },
            timeout=10,
        )
        submit_time = time.time() - start

        if resp.status_code == 200:
            data = resp.json()
            task_id = data["task_id"]
            print(f"✅ 任务提交成功！")
            print(f"   task_id: {task_id}")
            print(f"   提交耗时: {submit_time:.2f}秒（非常快！）")

            # 2. 轮询结果
            print("\n[2] 轮询任务状态...")
            for i in range(30):
                await asyncio.sleep(3)

                status_resp = await client.get(
                    f"{BASE_URL}/api/chat/async/{task_id}", timeout=10
                )

                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")
                    print(f"   [{i+1}] 状态: {status}")

                    if status == "completed":
                        result = status_data.get("result", {})
                        answer = result.get("answer", "")[:100]
                        print(f"\n✅ 任务完成！")
                        print(f"   答案: {answer}...")
                        total_time = time.time() - start
                        print(f"   总耗时: {total_time:.2f}秒")
                        return True
                    elif status == "failed":
                        print(f"\n❌ 任务失败: {status_data.get('error')}")
                        return False
            print("\n⚠️ 任务执行时间较长，请继续等待...")
            return True
        else:
            print(f"❌ 提交失败: {resp.status_code}")
            print(f"   响应: {resp.text}")
            return False


async def test_concurrent_async():
    """测试并发异步任务"""
    print("\n" + "=" * 60)
    print("  测试并发异步任务 (3个)")
    print("=" * 60)

    queries = ["苏轼是谁？", "水调歌头的主要内容是什么？", "乌台诗案是怎么回事？"]

    async with httpx.AsyncClient(timeout=120) as client:
        # 1. 同时提交多个任务
        print("\n[1] 同时提交 3 个任务...")
        start = time.time()

        submit_tasks = []
        for i, query in enumerate(queries):
            submit_tasks.append(
                client.post(
                    f"{BASE_URL}/api/chat/async",
                    json={
                        "message": query,
                        "session_id": f"concurrent_test_{i}",
                        "use_rag": True,
                        "top_k": 3,
                    },
                    timeout=10,
                )
            )

        responses = await asyncio.gather(*submit_tasks)

        task_ids = []
        for i, resp in enumerate(responses):
            if resp.status_code == 200:
                data = resp.json()
                task_ids.append(data["task_id"])
                print(f"   [{i+1}] ✅ task_id: {data['task_id'][:20]}...")
            else:
                print(f"   [{i+1}] ❌ 提交失败")

        submit_time = time.time() - start
        print(f"\n   全部提交耗时: {submit_time:.2f}秒")

        if not task_ids:
            return False

        # 2. 并行轮询
        print("\n[2] 并行轮询结果...")

        async def poll_single(task_id, index):
            for i in range(30):
                await asyncio.sleep(3)

                status_resp = await client.get(
                    f"{BASE_URL}/api/chat/async/{task_id}", timeout=10
                )

                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get("status")

                    if status == "completed":
                        answer = status_data.get("result", {}).get("answer", "")[:50]
                        print(f"   [{index+1}] ✅ 完成 - {answer}...")
                        return True
                    elif status == "failed":
                        print(f"   [{index+1}] ❌ 失败")
                        return False

                # 每5次打印一次状态
                if i % 5 == 0:
                    print(f"   [{index+1}] 轮询中 ({i})")

            print(f"   [{index+1}] ⚠️ 超时")
            return False

        poll_tasks = [poll_single(task_id, i) for i, task_id in enumerate(task_ids)]
        results = await asyncio.gather(*poll_tasks)

        success_count = sum(results)
        print(f"\n   📊 完成: {success_count}/{len(task_ids)}")

        return success_count > 0


async def main():
    print("=" * 60)
    print("  前端异步功能测试")
    print("=" * 60)

    # 检查服务状态
    print("\n检查服务状态...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                print("✅ 后端服务正常")
            else:
                print(f"⚠️ 后端状态: {resp.status_code}")
    except Exception as e:
        print(f"❌ 无法连接后端: {e}")
        print("\n请确保后端服务运行在端口 8000")
        return

    # 测试1: 单个异步任务
    test1_ok = await test_async_api()

    # 测试2: 并发异步任务
    test2_ok = await test_concurrent_async()

    # 总结
    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print(f"  单个异步任务: {'✅ 通过' if test1_ok else '❌ 失败'}")
    print(f"  并发异步任务: {'✅ 通过' if test2_ok else '❌ 失败'}")
    print("\n  前端测试说明:")
    print("  1. 打开浏览器访问: http://localhost:5173")
    print("  2. 在输入框右侧选择 '异步' 模式")
    print("  3. 发送消息，观察状态变化")
    print("  4. 可以连续发送多个消息")


if __name__ == "__main__":
    asyncio.run(main())
