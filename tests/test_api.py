"""测试 API"""
import requests

response = requests.post(
    "http://localhost:8000/api/chat",
    json={"message": "苏轼的代表作有哪些", "use_rag": True}
)

print("状态码:", response.status_code)
print("响应:", response.json())
