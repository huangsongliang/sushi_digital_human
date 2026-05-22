"""系统集成测试 - 核心功能测试"""

import os


class TestSystemCore:
    """系统核心测试"""

    def test_health_endpoint(self):
        """测试健康检查端点"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_root_endpoint(self):
        """测试根路径端点"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_chat_api(self):
        """测试聊天API"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/api/chat", json={"message": "hello"})
        assert response.status_code == 200

    def test_agent_api(self):
        """测试Agent API"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/agent/chat", json={"query": "hello"})
        assert response.status_code == 200

    def test_alerts_api(self):
        """测试告警API"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.get("/alerts/summary")
        assert response.status_code == 200

    def test_summary_api(self):
        """测试总结API"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.post("/summary/text", json={"content": "test content for summarization", "type": "brief"})
        assert response.status_code == 200

    def test_docs_available(self):
        """测试API文档"""
        from fastapi.testclient import TestClient
        from backend.main import app
        client = TestClient(app)
        response = client.get("/docs")
        assert response.status_code == 200

    def test_rag_chain_import(self):
        """测试RAG链导入"""
        from backend.chain.rag_chain import get_rag_chain
        rag_chain = get_rag_chain()
        assert rag_chain is not None

    def test_agent_manager_import(self):
        """测试Agent管理器导入"""
        from backend.agent import get_agent_manager
        agent_manager = get_agent_manager()
        assert agent_manager is not None

    def test_settings_import(self):
        """测试配置导入"""
        from backend.core.config import settings
        assert settings is not None