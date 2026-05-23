"""快速性能测试 - 简化版"""

import asyncio
import time
import statistics
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"


async def send_request(client, query):
    """发送单个请求"""
    start_time = time.time()
    try:
        response = await client.post(
            f"{BASE_URL}/api/chat",
            json={
                "message": query,
                "session_id": f"perf_{time.time()}",
                "use_rag": True,
                "top_k": 3,
            },
            timeout=30.0,
        )
        return {
            "success": response.status_code == 200,
            "response_time": time.time() - start_time,
        }
    except Exception as e:
        return {
            "success": False,
            "response_time": time.time() - start_time,
            "error": str(e),
        }


async def run_load_test(concurrent_users, requests_per_user):
    """运行负载测试"""
    print(f"\n开始测试: {concurrent_users} 并发用户, 每个 {requests_per_user} 请求")

    queries = [
        "苏轼是谁？",
        "《水调歌头》的主要内容",
        "苏轼在黄州期间写了什么作品？",
        "乌台诗案是什么？",
        "苏轼与王安石的关系",
    ]

    start_time = time.time()
    response_times = []
    success_count = 0
    fail_count = 0

    async def user_session(user_id):
        nonlocal success_count, fail_count
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(requests_per_user):
                query = queries[user_id % len(queries)]
                result = await send_request(client, query)
                response_times.append(result["response_time"])
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1

    tasks = [user_session(i) for i in range(concurrent_users)]
    await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    total_requests = success_count + fail_count

    sorted_times = sorted(response_times)

    return {
        "concurrent_users": concurrent_users,
        "total_requests": total_requests,
        "successful": success_count,
        "failed": fail_count,
        "error_rate": (fail_count / total_requests * 100) if total_requests > 0 else 0,
        "avg_response_time": statistics.mean(response_times) if response_times else 0,
        "min_response_time": min(response_times) if response_times else 0,
        "max_response_time": max(response_times) if response_times else 0,
        "p50": sorted_times[len(sorted_times) // 2] if sorted_times else 0,
        "p95": sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0,
        "p99": sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0,
        "throughput": total_requests / total_time if total_time > 0 else 0,
        "total_time": total_time,
    }


async def main():
    """主函数"""
    print("=" * 70)
    print("苏轼文化数字人 - 快速性能测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 健康检查
    print("\n检查服务状态...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("服务状态: 健康")
            else:
                print(f"服务状态: 异常 ({response.status_code})")
                return
    except Exception as e:
        print(f"服务状态: 无法连接 ({e})")
        return

    # 测试场景
    test_scenarios = [
        (5, 3, "极轻负载"),
        (10, 3, "正常负载"),
        (20, 3, "中等负载"),
        (30, 2, "较高负载"),
    ]

    results = []

    for concurrent, requests, name in test_scenarios:
        result = await run_load_test(concurrent, requests)
        result["name"] = name
        results.append(result)

        print(f"\n{name}结果:")
        print(
            f"  - 总请求: {result['total_requests']}, 成功: {result['successful']}, 失败: {result['failed']}"
        )
        print(f"  - 错误率: {result['error_rate']:.2f}%")
        print(f"  - 平均响应时间: {result['avg_response_time']:.2f}s")
        print(f"  - P95响应时间: {result['p95']:.2f}s")
        print(f"  - 吞吐量: {result['throughput']:.2f} req/s")

        # 测试间隔
        await asyncio.sleep(2)

    # 生成报告
    print("\n" + "=" * 70)
    print("性能测试报告摘要")
    print("=" * 70)
    print(
        f"\n{'负载级别':<10} {'并发':<6} {'成功率':<10} {'平均响应':<12} {'P95响应':<12} {'吞吐量':<12}"
    )
    print("-" * 70)

    for result in results:
        success_rate = 100 - result["error_rate"]
        print(
            f"{result['name']:<10} {result['concurrent_users']:<6} {success_rate:>6.2f}%    "
            f"{result['avg_response_time']:>8.2f}s    {result['p95']:>8.2f}s    "
            f"{result['throughput']:>8.2f} req/s"
        )

    print("\n性能评估:")
    for result in results:
        issues = []
        if result["p95"] > 5.0:
            issues.append("P95响应时间过高")
        if result["error_rate"] > 5.0:
            issues.append("错误率较高")
        if result["throughput"] < 5.0:
            issues.append("吞吐量偏低")

        if issues:
            print(f"  - {result['name']}: {'; '.join(issues)}")
        else:
            print(f"  - {result['name']}: 正常")

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
