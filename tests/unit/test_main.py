"""主应用模块单元测试"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestMainApp:
    """主应用测试"""

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_health_liveness(self):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_readiness(self):
        response = client.get("/health/readiness")
        assert response.status_code == 200 or response.status_code == 503
