"""
完整的 API 接口测试
测试所有 API 端点：认证、聊天、文档管理等
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self):
        self.token = None
        self.test_results = []

    def test_endpoint(self, method: str, endpoint: str, data: Dict = None,
                    headers: Dict = None, description: str = "",
                    timeout: float = 5.0) -> Dict[str, Any]:
        """测试单个 API 端点

        Args:
            method: HTTP 方法
            endpoint: API 路径
            data: 请求数据
            headers: 请求头
            description: 测试描述
            timeout: 超时时间（秒），根据 API 类型调整
        """
        url = f"{BASE_URL}{endpoint}"
        if headers is None:
            headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            request_start = time.time()
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                return {"status": "error", "message": f"不支持的方法: {method}"}

            elapsed = time.time() - request_start

            result = {
                "endpoint": f"{method} {endpoint}",
                "description": description,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response": response.json() if response.content else None
            }
            self.test_results.append(result)

            status = "✅" if result["success"] else "❌"
            print(f"{status} {method} {endpoint} - {description}: {response.status_code}")
            return result

        except Exception as e:
            error_result = {
                "endpoint": f"{method} {endpoint}",
                "description": description,
                "success": False,
                "error": str(e)
            }
            self.test_results.append(error_result)
            print(f"❌ {method} {endpoint} - {description}: 错误 - {e}")
            return error_result

    def test_health_endpoints(self):
        """测试健康检查端点"""
        print("\n" + "="*60)
        print("🩺 健康检查端点测试")
        print("="*60)

        self.test_endpoint("GET", "/health", description="健康检查")
        self.test_endpoint("GET", "/health/live", description="存活检查")
        self.test_endpoint("GET", "/health/ready", description="就绪检查")
        self.test_endpoint("GET", "/metrics", description="Prometheus 指标")

    def test_auth_endpoints(self):
        """测试认证端点"""
        print("\n" + "="*60)
        print("🔐 认证端点测试")
        print("="*60)

        # 注册
        register_data = {
            "username": "testuser_" + str(int(__import__('time').time())),
            "email": f"test_{int(__import__('time').time())}@example.com",
            "password": "testpass123"
        }
        result = self.test_endpoint("POST", "/api/auth/register",
                                   data=register_data,
                                   description="用户注册")

        # 登录
        login_data = {
            "email": register_data["email"],
            "password": register_data["password"]
        }
        result = self.test_endpoint("POST", "/api/auth/login",
                                   data=login_data,
                                   description="用户登录")
        if result.get("success") and result.get("response"):
            self.token = result["response"].get("access_token")

        # 获取当前用户信息
        self.test_endpoint("GET", "/api/auth/me",
                          description="获取当前用户信息")

        # 获取角色列表
        self.test_endpoint("GET", "/api/auth/roles",
                          description="获取角色列表")

        # 获取权限列表
        self.test_endpoint("GET", "/api/auth/permissions",
                          description="获取权限列表")

    def test_chat_endpoints(self):
        """测试聊天端点"""
        print("\n" + "="*60)
        print("💬 聊天端点测试")
        print("="*60)

        # 同步聊天
        chat_data = {
            "message": "你好，请介绍一下你自己",
            "session_id": "test_session_001",
            "use_rag": True,
            "top_k": 3
        }
        self.test_endpoint("POST", "/api/chat",
                          data=chat_data,
                          description="同步聊天")

        # 流式聊天
        self.test_endpoint("POST", "/api/chat/stream",
                          data=chat_data,
                          description="流式聊天")

    def test_document_endpoints(self):
        """测试文档管理端点"""
        print("\n" + "="*60)
        print("📚 文档管理端点测试")
        print("="*60)

        # 获取文档列表
        self.test_endpoint("GET", "/api/documents/list",
                          description="获取文档列表")

        # 获取文档统计
        self.test_endpoint("GET", "/api/documents/stats",
                          description="获取文档统计")

    def test_admin_endpoints(self):
        """测试管理端点"""
        print("\n" + "="*60)
        print("⚙️ 管理端点测试")
        print("="*60)

        # 健康检查
        self.test_endpoint("GET", "/api/alerts/health",
                          description="告警健康检查")

    def test_root_endpoints(self):
        """测试根路径端点"""
        print("\n" + "="*60)
        print("🏠 根路径端点测试")
        print("="*60)

        self.test_endpoint("GET", "/", description="根路径")
        self.test_endpoint("GET", "/docs", description="API 文档")

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("🚀 企业级智能文档问答平台 - API 完整测试")
        print("="*60)
        print(f"测试地址: {BASE_URL}")
        print(f"开始时间: {__import__('datetime').datetime.now()}")

        # 按优先级测试
        self.test_root_endpoints()
        self.test_health_endpoints()
        self.test_auth_endpoints()
        self.test_chat_endpoints()
        self.test_document_endpoints()
        self.test_admin_endpoints()

        # 汇总结果
        print("\n" + "="*60)
        print("📊 测试结果汇总")
        print("="*60)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get("success", False))
        failed = total - passed

        print(f"总测试数: {total}")
        print(f"通过: {passed} ({passed/total*100:.1f}%)")
        print(f"失败: {failed} ({failed/total*100:.1f}%)")

        if failed > 0:
            print("\n失败的测试:")
            for r in self.test_results:
                if not r.get("success", False):
                    print(f"  - {r['endpoint']}: {r.get('error', r.get('status_code', '未知错误'))}")

        return passed == total

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
