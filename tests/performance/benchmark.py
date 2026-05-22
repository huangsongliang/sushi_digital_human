"""
Simple performance benchmark script
"""
import asyncio
import aiohttp
import time
from typing import List, Dict, Any
import statistics


async def test_health(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Test health check endpoint"""
    start = time.time()
    try:
        async with session.get("http://localhost:8000/health") as resp:
            await resp.text()
            elapsed = time.time() - start
            return {
                "success": True,
                "status": resp.status,
                "latency": elapsed
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "error": str(e),
            "latency": elapsed
        }


async def test_chat(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """Test chat endpoint"""
    start = time.time()
    try:
        async with session.post(
            "http://localhost:8000/api/chat",
            json={"message": "Hello, please introduce yourself"}
        ) as resp:
            await resp.text()
            elapsed = time.time() - start
            return {
                "success": True,
                "status": resp.status,
                "latency": elapsed
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "success": False,
            "error": str(e),
            "latency": elapsed
        }


async def run_concurrent_tests(test_func, concurrency: int, iterations: int) -> List[Dict]:
    """Run concurrent tests"""
    results = []
    for i in range(iterations):
        async with aiohttp.ClientSession() as session:
            tasks = [test_func(session) for _ in range(concurrency)]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
        await asyncio.sleep(0.5)
    return results


def analyze_results(results: List[Dict], test_name: str) -> Dict:
    """Analyze test results"""
    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count
    latencies = [r["latency"] for r in results if r["success"]]
    
    if latencies:
        avg_latency = statistics.mean(latencies)
        p50_latency = statistics.median(latencies)
        sorted_latencies = sorted(latencies)
        p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        max_latency = max(latencies)
        min_latency = min(latencies)
    else:
        avg_latency = p50_latency = p95_latency = max_latency = min_latency = 0
    
    return {
        "test_name": test_name,
        "total_requests": len(results),
        "success_rate": f"{(success_count / len(results) * 100):.1f}%" if len(results) > 0 else "0%",
        "avg_latency_ms": f"{avg_latency * 1000:.2f}",
        "p50_latency_ms": f"{p50_latency * 1000:.2f}",
        "p95_latency_ms": f"{p95_latency * 1000:.2f}",
        "max_latency_ms": f"{max_latency * 1000:.2f}",
        "min_latency_ms": f"{min_latency * 1000:.2f}",
        "success_count": success_count,
        "failed_count": failed_count
    }


async def main():
    print("=" * 70)
    print("[START] System Performance Benchmark")
    print("=" * 70)
    print()
    
    print("[1] Health Check Endpoint (Low Concurrency)")
    health_results = await run_concurrent_tests(test_health, concurrency=3, iterations=10)
    health_analysis = analyze_results(health_results, "Health Check")
    
    print()
    print("[2] Health Check Endpoint (High Concurrency)")
    health_results_high = await run_concurrent_tests(test_health, concurrency=10, iterations=5)
    health_analysis_high = analyze_results(health_results_high, "Health Check (High)")
    
    print()
    print("[3] Chat API Endpoint (Low Concurrency)")
    chat_results = await run_concurrent_tests(test_chat, concurrency=2, iterations=5)
    chat_analysis = analyze_results(chat_results, "Chat API")
    
    print()
    print("=" * 70)
    print("[RESULTS] Summary")
    print("=" * 70)
    
    for analysis in [health_analysis, health_analysis_high, chat_analysis]:
        print()
        print(f"[+] {analysis['test_name']}")
        print(f"  Total Requests: {analysis['total_requests']}")
        print(f"  Success Rate:   {analysis['success_rate']}")
        print(f"  Avg Latency:    {analysis['avg_latency_ms']}ms")
        print(f"  P50 Latency:    {analysis['p50_latency_ms']}ms")
        print(f"  P95 Latency:    {analysis['p95_latency_ms']}ms")
        print(f"  Max Latency:    {analysis['max_latency_ms']}ms")
        print(f"  Min Latency:    {analysis['min_latency_ms']}ms")
        print(f"  Success:        {analysis['success_count']}, Failed: {analysis['failed_count']}")
    
    print()
    print("=" * 70)
    print("[DONE] Benchmark Completed!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Test interrupted")
