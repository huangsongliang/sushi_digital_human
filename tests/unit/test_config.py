"""
配置模块测试
"""

import pytest
from backend.core.config import Settings


class TestSettings:
    """Settings 配置测试"""

    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()
        assert settings.embedding_model == "text-embedding-v2"
        assert settings.llm_model == "qwen-max"
        assert settings.embedding_dimension == 1536

    def test_redis_config(self):
        """测试 Redis 配置"""
        settings = Settings()
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_max_connections == 50

    def test_mysql_config(self):
        """测试 MySQL 配置"""
        settings = Settings()
        assert settings.mysql_host == "localhost"
        assert settings.mysql_port == 3306
        assert settings.mysql_database == "sushi"

    def test_chroma_config(self):
        """测试 ChromaDB 配置"""
        settings = Settings()
        assert settings.chroma_persist_dir is not None

    def test_rag_config(self):
        """测试 RAG 配置"""
        settings = Settings()
        assert settings.top_k >= 1
        assert settings.rerank_top_k >= 1
        assert settings.vector_weight >= 0
        assert settings.bm25_weight >= 0

    def test_rate_limit_config(self):
        """测试限流配置"""
        settings = Settings()
        assert settings.rate_limit_per_minute >= 1

    def test_security_config(self):
        """测试安全配置"""
        settings = Settings()
        assert settings.secret_key is not None
        assert settings.access_token_expire_minutes >= 1

    def test_app_config(self):
        """测试应用配置"""
        settings = Settings()
        assert settings.app_name is not None
        assert settings.app_version is not None

    def test_log_config(self):
        """测试日志配置"""
        settings = Settings()
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
