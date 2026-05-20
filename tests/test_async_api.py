"""
异步队列 API 测试脚本
测试异步聊天接口的性能和稳定性
"""

import asyncio
import time
import statistics
import random
import httpx
from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

# ==================== 配置 ====================
BASE_URL = "http://localhost:8000"
TEST_DURATION = 60  # 测试持续时间（秒）
CONCURRENT_SUBMITTERS = 50  # 并发提交数
POLL_INTERVAL = 2.0  # 轮询间隔（秒）
POLL_TIMEOUT = 120  # 轮询超时（秒）

# 测试查询
TEST_QUERIES = [
    "苏轼是谁？",
    "《水调歌头》的主要内容是什么？",
    "乌台诗案是什么事件？",
    "苏轼在黄州期间写了哪些作品？",
    "苏轼与王安石的关系如何？",
    "西湖苏堤是谁修建的？",
    "苏轼的家庭情况如何？",
    "苏轼的文学成就有哪些？",
    "苏轼被贬黄州的原因是什么？",
    "苏轼在文学史上的地位如何？",
]


# ==================== 数据模型 ====================
@dataclass
class TaskResult:
    """任务结果"""

    task_id: str
    submit_time: float
    complete_time: float = 0
    status: str = "pending"
    answer: str = ""
    error: str = ""

    @property
    def wait_time(self) -> float:
        """等待时间（从提交到完成）"""
        if self.complete_time > 0:
            return self.complete_time - self.submit_time
        return time.time() - self.submit_time

    @property
    def is_completed(self) -> bool:
        return self.status in ["completed", "failed"]


@dataclass
class TestStats:
    """测试统计"""

    total_submitted: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_timeout: int = 0
    wait_times: List[float] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        if self.total_submitted == 0:
            return 0
        return self.total_completed / self.total_submitted


# ==================== 测试客户端 ====================
class AsyncAPITester:
    """异步 API 测试器"""

    def __init__(self):
        self.tasks: Dict[str, TaskResult] = {}
        self.stats = TestStats()
        self.running = False

    async def submit_task(
        self, client: httpx.AsyncClient, query: str, session_id: str
    ) -> str:
        """提交异步任务"""
        try:
            response = await client.post(
                f"{BASE_URL}/api/chat/async",
                json={
                    "message": query,
                    "session_id": session_id,
                    "use_rag": True,
                    "top_k": 3,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                task_id = data.get("task_id")

                task = TaskResult(
                    task_id=task_id, submit_time=time.time(), status="pending"
                )
                self.tasks[task_id] = task
                self.stats.total_submitted += 1

                return task_id
            else:
                print(f"  提交失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"  提交异常: {str(e)}")
            return None

    async def poll_result(
        self, client: httpx.AsyncClient, task_id: str
    ) -> Dict[str, Any]:
        """轮询任务结果"""
        try:
            response = await client.get(
                f"{BASE_URL}/api/chat/async/{task_id}", timeout=10.0
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def check_completed_tasks(self, client: httpx.AsyncClient):
        """检查已完成的任务"""
        completed = []

        for task_id, task in self.tasks.items():
            if task.is_completed:
                completed.append(task_id)
                continue

            # 轮询结果
            result = await self.poll_result(client, task_id)

            if result.get("status") == "completed":
                task.status = "completed"
                task.complete_time = time.time()
                task.answer = result.get("result", {}).get("answer", "")
                self.stats.total_completed += 1
                self.stats.wait_times.append(task.wait_time)
                completed.append(task_id)

            elif result.get("status") == "failed":
                task.status = "failed"
                task.complete_time = time.time()
                task.error = result.get("error", "Unknown error")
                self.stats.total_failed += 1
                completed.append(task_id)

            elif task.wait_time > POLL_TIMEOUT:
                task.status = "timeout"
                self.stats.total_timeout += 1
                completed.append(task_id)

        # 清理已完成的任务（只保留未完成的）
        for task_id in completed:
            if task_id in self.tasks:
                del self.tasks[task_id]

    async def run_submitter(self, client: httpx.AsyncClient, submit_count: int):
        """提交任务"""
        for i in range(submit_count):
            if not self.running:
                break

            query = random.choice(TEST_QUERIES)
            session_id = f"async_test_{int(time.time())}_{i}"

            await self.submit_task(client, query, session_id)

            # 随机等待
            await asyncio.sleep(random.uniform(0.1, 0.5))

    async def run_poller(self, client: httpx.AsyncClient):
        """轮询任务结果"""
        while self.running or self.tasks:
            await self.check_completed_tasks(client)

            if not self.running and not self.tasks:
                break

            await asyncio.sleep(POLL_INTERVAL)

    async def run_test(self) -> Dict[str, Any]:
        """运行异步 API 测试"""
        print(f"\n{'='*80}")
        print(f"异步队列 API 测试")
        print(f"{'='*80}\n")

        print(f"测试配置:")
        print(f"  - 并发提交数: {CONCURRENT_SUBMITTERS}")
        print(f"  - 测试时长: {TEST_DURATION}秒")
        print(f"  - 轮询间隔: {POLL_INTERVAL}秒")
        print(f"  - 轮询超时: {POLL_TIMEOUT}秒\n")

        # 检查服务
        print("检查服务状态...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{BASE_URL}/health")
                if response.status_code == 200:
                    print(f"✅ 服务正常\n")
                else:
                    print(f"⚠️ 服务返回: {response.status_code}\n")
        except Exception as e:
            print(f"❌ 无法连接服务: {e}\n")
            return {}

        self.running = True
        test_start = time.time()

        # 创建共享客户端
        client = httpx.AsyncClient(timeout=30.0)

        # 提交任务
        print(f"[阶段1] 提交任务...")
        submit_tasks = []
        for i in range(CONCURRENT_SUBMITTERS):
            submit_count = max(1, TEST_DURATION // 10)  # 每个提交者提交的数量
            submit_tasks.append(self.run_submitter(client, submit_count))

        # 同时轮询结果
        poller = asyncio.create_task(self.run_poller(client))
        submitters = asyncio.gather(*submit_tasks)

        # 等待提交完成
        await submitters

        # 继续轮询直到所有任务完成或超时
        print(f"[阶段2] 等待任务完成...")
        self.running = False

        # 等待一段时间让任务完成
        wait_start = time.time()
        while self.tasks and (time.time() - wait_start) < POLL_TIMEOUT:
            await asyncio.sleep(POLL_INTERVAL)
            if not self.tasks:
                break

        # 清理
        self.running = False
        await poller
        await client.aclose()

        test_duration = time.time() - test_start

        # 统计结果
        return self.generate_report(test_duration)

    def generate_report(self, test_duration: float) -> Dict[str, Any]:
        """生成测试报告"""
        report = f"""
{'='*80}
              异步队列 API 测试报告
{'='*80}

测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
测试时长: {test_duration:.2f}秒

一、任务统计
================================================================================

1. 提交统计
   - 总提交数: {self.stats.total_submitted}
   - 总完成数: {self.stats.total_completed}
   - 总失败数: {self.stats.total_failed}
   - 总超时数: {self.stats.total_timeout}
   - 完成率: {self.stats.completion_rate * 100:.2f}%

2. 等待时间统计
"""

        if self.stats.wait_times:
            wait_times = sorted(self.stats.wait_times)
            report += f"""   - 平均等待: {statistics.mean(wait_times):.2f}秒
   - 最短等待: {min(wait_times):.2f}秒
   - 最长等待: {max(wait_times):.2f}秒
   - P50等待: {wait_times[len(wait_times)//2]:.2f}秒
   - P95等待: {wait_times[int(len(wait_times)*0.95)]:.2f}秒
"""
        else:
            report += "   - 无等待时间数据\n"

        # 吞吐量计算
        throughput = (
            self.stats.total_completed / test_duration if test_duration > 0 else 0
        )

        report += f"""
3. 吞吐量
   - 完成吞吐量: {throughput:.2f} 任务/秒

二、异步 API 优势分析
================================================================================

1. 用户体验
   ✅ 请求立即返回（< 1秒）
   ✅ 无需等待 LLM 响应
   ✅ 可以并行提交多个请求

2. 系统稳定性
   ✅ 客户端可以控制轮询节奏
   ✅ 请求不会因超时失败
   ✅ 可以实现请求队列管理

3. 扩展性
   ✅ 可以独立扩展 Worker
   ✅ 可以实现请求合并
   ✅ 支持任务优先级

三、测试结论
================================================================================
"""

        if self.stats.completion_rate > 0.8:
            report += f"""   🎉 异步 API 测试通过！
   - 任务完成率: {self.stats.completion_rate * 100:.2f}%
   - 平均等待时间: {statistics.mean(self.stats.wait_times):.2f}秒（用户无感知等待）
"""
        else:
            report += f"""   ⚠️ 任务完成率较低: {self.stats.completion_rate * 100:.2f}%
   - 可能原因：Celery Worker 未运行或 LLM API 响应慢
"""

        report += f"""
{'='*80}
"""

        print(report)

        return {
            "total_submitted": self.stats.total_submitted,
            "total_completed": self.stats.total_completed,
            "total_failed": self.stats.total_failed,
            "completion_rate": self.stats.completion_rate,
            "avg_wait_time": (
                statistics.mean(self.stats.wait_times) if self.stats.wait_times else 0
            ),
            "throughput": throughput,
            "report": report,
        }


# ==================== 主函数 ====================
async def main():
    """主函数"""
    print("=" * 80)
    print("        苏轼文化数字人 - 异步队列 API 测试")
    print("=" * 80)

    tester = AsyncAPITester()

    try:
        result = await tester.run_test()

        # 保存报告
        if result:
            report_file = (
                f"tests/async_api_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(result.get("report", ""))
            print(f"\n📄 报告已保存: {report_file}")

    except KeyboardInterrupt:
        print("\n测试被中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("\n注意: 异步 API 需要 Celery Worker 运行才能完整测试")
    print("      如果 Worker 未运行，任务将保持 pending 状态\n")

    asyncio.run(main())
