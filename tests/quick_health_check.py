"""快速健康检查"""

import asyncio
import httpx


async def check_health():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            print(f"健康检查: {response.status_code}")
            print(f"响应: {response.json()}")

            # 测试聊天API
            chat_response = await client.post(
                "http://localhost:8000/api/chat",
                json={
                    "message": "苏轼是谁？",
                    "session_id": "test",
                    "use_rag": True,
                    "top_k": 3,
                },
            )
            print(f"\n聊天API: {chat_response.status_code}")
            result = chat_response.json()
            print(f"回答长度: {len(result.get('answer', ''))} 字符")
            return True
    except Exception as e:
        print(f"错误: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(check_health())
