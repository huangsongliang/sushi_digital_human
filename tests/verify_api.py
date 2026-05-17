"""最简单的API验证"""
import httpx
import time

BASE_URL = "http://localhost:8000"

print("=== 验证API ===")

# 1. 测试健康检查
print("\n1. 健康检查:")
try:
    response = httpx.get(f"{BASE_URL}/health", timeout=5)
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.text}")
except Exception as e:
    print(f"   错误: {e}")

# 2. 测试单个同步请求
print("\n2. 单个同步请求:")
try:
    start = time.time()
    response = httpx.post(
        f"{BASE_URL}/api/chat",
        json={
            "message": "苏轼是谁？",
            "session_id": "simple_test",
            "use_rag": True,
            "top_k": 3
        },
        timeout=60
    )
    elapsed = time.time() - start
    print(f"   状态码: {response.status_code}")
    print(f"   耗时: {elapsed:.2f}秒")
    if response.status_code == 200:
        data = response.json()
        print(f"   答案: {data.get('answer', '')[:150]}...")
except Exception as e:
    print(f"   错误: {e}")

# 3. 测试单个异步请求
print("\n3. 单个异步请求（提交+轮询）:")
try:
    # 提交
    start_submit = time.time()
    resp = httpx.post(
        f"{BASE_URL}/api/chat/async",
        json={
            "message": "乌台诗案是什么？",
            "session_id": "async_test",
            "use_rag": True,
            "top_k": 3
        },
        timeout=10
    )
    submit_time = time.time() - start_submit
    
    if resp.status_code == 200:
        task_id = resp.json()['task_id']
        print(f"   提交成功, task_id: {task_id}")
        print(f"   提交耗时: {submit_time:.2f}秒 (用户体验很好!)")
        
        # 轮询
        print("\n   轮询结果:")
        for i in range(20):
            time.sleep(2)
            check_resp = httpx.get(f"{BASE_URL}/api/chat/async/{task_id}", timeout=5)
            if check_resp.status_code == 200:
                data = check_resp.json()
                status = data.get('status')
                print(f"   [{i+1}] {status}", end="")
                if status == 'completed':
                    print(" ✅ 完成!")
                    answer = data.get('result', {}).get('answer', '')
                    print(f"   答案: {answer[:150]}...")
                    break
                elif status == 'failed':
                    print(" ❌ 失败")
                    print(f"   错误: {data.get('error', '')}")
                    break
                else:
                    print("...")
                    
except Exception as e:
    print(f"   错误: {e}")
    import traceback
    traceback.print_exc()
