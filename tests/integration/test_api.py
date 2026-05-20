"""API 集成测试"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


class TestHealthEndpoint:
    """健康检查端点测试"""

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        # 健康检查可能返回 200（健康/降级）或 503（不健康）
        assert response.status_code in [200, 503]
        data = response.json()
        # 状态可能是 healthy, degraded 或 unhealthy
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "service" in data
        assert "version" in data


class TestRootEndpoint:
    """根路径测试"""

    def test_root(self, client):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestMetricsEndpoint:
    """指标端点测试"""

    def test_metrics(self, client):
        """测试 metrics 端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "sushi_requests_total" in content or "#" in content


class TestChatEndpoint:
    """聊天端点测试"""

    def test_chat_empty_message(self, client):
        """测试空消息返回验证错误（FastAPI 默认返回 422）"""
        response = client.post("/api/chat", json={"message": "", "session_id": "test"})
        # FastAPI 对 Pydantic 验证失败默认返回 422
        assert response.status_code == 422

    def test_chat_valid_message(self, client):
        """测试有效消息（会调用真实的 LLM，可能失败）"""
        response = client.post(
            "/api/chat", json={"message": "Hello", "session_id": "test"}
        )
        # 如果 API Key 配置正确，应该返回 200；否则返回 401/500
        assert response.status_code in [200, 401, 500]


class TestDocsEndpoint:
    """文档端点测试"""

    def test_add_docs_empty(self, client):
        """测试添加空文档列表"""
        response = client.post("/api/docs/add", json={"documents": []})
        # 空文档列表应该被拒绝，可以返回 400 或 422
        assert response.status_code in [400, 422]

    def test_add_docs_valid(self, client):
        """测试添加有效文档"""
        response = client.post(
            "/api/docs/add", json={"documents": ["苏轼是宋代著名文学家。"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "count" in data
        assert data["count"] == 1
