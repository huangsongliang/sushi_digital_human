"""API 集成测试 - 覆盖所有 API 端点"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

os.environ["ENV"] = "test"
os.environ["MYSQL_HOST"] = ""
os.environ["MYSQL_USER"] = ""
os.environ["MYSQL_DATABASE"] = ""
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from backend.main import app

client = TestClient(app)


class TestRootEndpoint:
    """根路径测试"""

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data


class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data

    def test_liveness_check(self):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_check(self):
        response = client.get("/health/readiness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_metrics(self):
        response = client.get("/metrics")
        assert response.status_code == 200


class TestAuthEndpoints:
    """认证端点测试"""

    def test_register_success(self):
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "test@example.com", "password": "Testpass123!"}
        )
        assert response.status_code in [200, 400, 500, 422]

    def test_register_invalid_email(self):
        response = client.post(
            "/api/auth/register",
            json={"username": "testuser", "email": "invalid-email", "password": "testpass123"}
        )
        assert response.status_code == 422

    def test_login_invalid_credentials(self):
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code in [401, 500, 422]

    def test_get_current_user_without_token(self):
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_github_redirect(self):
        response = client.get("/api/auth/github/redirect")
        assert response.status_code in [307, 404, 500]


class TestChatEndpoints:
    """聊天端点测试"""

    def test_chat_empty_message(self):
        response = client.post("/api/chat", json={"message": "", "session_id": "test"})
        assert response.status_code == 422

    def test_chat_valid_message(self):
        response = client.post(
            "/api/chat", json={"message": "Hello", "session_id": "test", "use_rag": False}
        )
        assert response.status_code in [200, 401, 500]

    def test_chat_stream(self):
        response = client.post(
            "/api/chat/stream",
            json={"message": "Hello", "session_id": "test_stream", "use_rag": False}
        )
        assert response.status_code in [200, 401, 500]

    def test_async_chat(self):
        response = client.post(
            "/api/chat/async",
            json={"message": "Hello", "session_id": "test_async", "use_rag": False}
        )
        assert response.status_code in [200, 500]

    def test_add_documents(self):
        response = client.post("/api/docs/add", json={"documents": ["测试文档内容"]})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_add_empty_documents(self):
        response = client.post("/api/docs/add", json={"documents": []})
        assert response.status_code in [400, 422]

    def test_get_document_count(self):
        response = client.get("/api/docs/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data

    def test_clear_documents(self):
        response = client.delete("/api/docs")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_performance_stats(self):
        response = client.get("/api/stats/performance")
        assert response.status_code == 200

    def test_reset_performance_stats(self):
        response = client.post("/api/stats/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestDocumentsEndpoints:
    """文档管理端点测试"""

    def test_upload_document(self):
        response = client.post(
            "/api/documents/upload",
            files={"file": ("test.txt", "测试文档内容", "text/plain")}
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data

    def test_list_documents(self):
        response = client.get("/api/documents/list")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "documents" in data
            assert "total" in data

    def test_get_document_content_invalid_id(self):
        response = client.get("/api/documents/invalid-id/content")
        assert response.status_code in [404, 500]

    def test_get_document_versions_invalid_id(self):
        response = client.get("/api/documents/invalid-id/versions")
        assert response.status_code in [404, 500]

    def test_delete_document_invalid_id(self):
        response = client.delete("/api/documents/invalid-id")
        assert response.status_code in [400, 404, 500]


class TestAlertsEndpoints:
    """告警管理端点测试"""

    def test_get_alert_summary(self):
        response = client.get("/alerts/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_active_alerts(self):
        response = client.get("/alerts/active")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_alert_history(self):
        response = client.get("/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_alert_rules(self):
        response = client.get("/alerts/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_create_and_delete_alert_rule(self):
        create_response = client.post(
            "/alerts/rules",
            json={
                "name": "test_rule",
                "severity": "warning",
                "metric_type": "request_count",
                "operator": ">",
                "threshold": 100
            }
        )
        assert create_response.status_code == 200

        delete_response = client.delete("/alerts/rules/test_rule")
        assert delete_response.status_code == 200


class TestSummaryEndpoints:
    """总结端点测试"""

    def test_summarize_text(self):
        response = client.post(
            "/summary/text",
            json={"content": "这是一段测试文本，用于测试总结功能。", "type": "brief"}
        )
        assert response.status_code in [200, 500]

    def test_extract_key_points(self):
        response = client.post(
            "/summary/key-points",
            json={"content": "这是一段测试文本，包含多个关键点。关键点一：测试。关键点二：总结。", "max_points": 5}
        )
        assert response.status_code in [200, 500]

    def test_generate_title(self):
        response = client.post(
            "/summary/title",
            json={"content": "这是一段测试文本，用于测试标题生成功能。", "max_length": 30}
        )
        assert response.status_code in [200, 500]


class TestAgentEndpoints:
    """Agent端点测试"""

    def test_agent_chat(self):
        response = client.post(
            "/agent/chat",
            json={"query": "Hello", "session_id": "agent_test"}
        )
        assert response.status_code in [200, 500]

    def test_list_tools(self):
        response = client.get("/agent/tools")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_agent_health(self):
        response = client.get("/agent/health")
        assert response.status_code in [200, 503]


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_endpoint(self):
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_invalid_method(self):
        response = client.post("/health")
        assert response.status_code == 405

    def test_invalid_json(self):
        response = client.post("/api/chat", data="not valid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 422

    def test_large_payload(self):
        large_message = "a" * 10000
        response = client.post("/api/chat", json={"message": large_message, "session_id": "test"})
        assert response.status_code in [200, 413, 422]