"""简单测试异步API"""

import httpx
import time

BASE_URL = "http://localhost:8000"

print("=== 测试异步API ===")

try:
    # 1. 先测试健康检查
    print("1. 健康检查...")
    response = httpx.get(f"{BASE_URL}/health")
    print(f"  状态码: {response.status_code}")
    print(f"  响应: {response.text}")
    print()

    # 2. 测试异步提交
    print("2. 提交异步任务...")
    response = httpx.post(
        f"{BASE_URL}/api/chat/async",
        json={
            "message": "苏轼是谁？",
            "session_id": "test123",
            "use_rag": True,
            "top_k": 3,
        },
        timeout=10,
    )
    print(f"  状态码: {response.status_code}")
    print(f"  响应: {response.text}")
    print()

    if response.status_code == 200:
        result = response.json()
        task_id = result.get("task_id")
        print(f"3. 查询任务状态 (task_id={task_id})...")

        # 轮询几次
        for i in range(5):
            time.sleep(3)
            status_resp = httpx.get(f"{BASE_URL}/api/chat/async/{task_id}", timeout=10)
            print(f"  [{i+1}] 状态码: {status_resp.status_code}")
            print(f"  [{i+1}] 响应: {status_resp.text}")
            if status_resp.status_code == 200:
                data = status_resp.json()
                if data.get("status") == "completed":
                    print(
                        f"  完成！答案: {data.get('result', {}).get('answer', '')[:100]}..."
                    )
                    break

except Exception as e:
    print(f"\n出错: {e}")
    import traceback

    traceback.print_exc()
