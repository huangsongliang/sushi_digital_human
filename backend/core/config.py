"""
配置管理模块
集中管理应用配置，支持：
- 环境变量读取
- Pydantic 数据验证
- 配置分层（开发/生产）
- 敏感信息脱敏
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import List, Optional
from pathlib import Path


class SettingsModelConfig(SettingsConfigDict):
    """Settings 配置字典的子类，用于类型注解"""

    pass


class Settings(BaseSettings):
    """
    应用配置类

    从环境变量读取配置，支持默认值和类型验证
    """

    # DashScope API 配置
    dashscope_api_key: str = Field(default="", description="DashScope API 密钥")

    # 模型配置
    embedding_model: str = Field(
        default="text-embedding-v2", description="嵌入模型名称"
    )
    llm_model: str = Field(default="qwen-max", description="大语言模型名称")
    embedding_dimension: int = Field(default=1536, description="嵌入向量维度")

    # Redis 配置
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis 连接地址"
    )
    redis_max_connections: int = Field(default=50, description="Redis 最大连接数")

    # MySQL 配置（可选）
    mysql_host: Optional[str] = Field(default="localhost", description="MySQL 主机地址")
    mysql_port: int = Field(default=3306, description="MySQL 端口")
    mysql_user: Optional[str] = Field(default="root", description="MySQL 用户名")
    mysql_password: Optional[str] = Field(default=None, description="MySQL 密码")
    mysql_database: Optional[str] = Field(default="sushi", description="MySQL 数据库名")

    # ChromaDB 配置
    chroma_persist_dir: Path = Field(
        default=Path(__file__).parent.parent.parent / "data" / "chroma_db",
        description="ChromaDB 持久化目录",
    )

    # 检索配置
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回的最相似文档数量")
    vector_weight: float = Field(default=0.7, ge=0, le=1, description="向量检索权重")
    bm25_weight: float = Field(default=0.3, ge=0, le=1, description="BM25 检索权重")
    rerank_top_k: int = Field(
        default=3, ge=1, le=10, description="重排序后返回的文档数量"
    )
    enable_reranking: bool = Field(default=True, description="是否启用重排序")

    # 安全配置
    secret_key: str = Field(
        default="change-this-secret-key-in-production", description="JWT 签名密钥"
    )
    access_token_expire_minutes: int = Field(
        default=30, ge=1, description="访问令牌过期时间（分钟）"
    )
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="允许的跨域来源",
    )
    rate_limit_per_minute: int = Field(
        default=60, ge=1, description="每分钟 API 调用限制"
    )

    # 应用配置
    app_name: str = Field(default="企业级智能文档问答平台", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")

    # 数据处理配置
    chunk_size: int = Field(
        default=500, ge=100, le=2000, description="文档分块大小（字符数）"
    )
    chunk_overlap: int = Field(
        default=50, ge=0, le=500, description="文档分块重叠大小（字符数）"
    )

    # LLM 调用配置
    llm_temperature: float = Field(default=0.7, ge=0, le=2, description="LLM 温度参数")
    llm_max_tokens: int = Field(
        default=2000, ge=100, le=8000, description="LLM 最大生成 token 数"
    )
    llm_timeout: int = Field(default=60, ge=10, description="LLM 调用超时时间（秒）")
    llm_max_retries: int = Field(default=3, ge=0, description="LLM 调用最大重试次数")

    # 阿里云配置
    aliyun_access_key_id: str = Field(default="", description="阿里云 AccessKey ID")
    aliyun_access_key_secret: str = Field(default="", description="阿里云 AccessKey Secret")

    # 短信服务配置
    sms_use_real_service: bool = Field(default=False, description="是否使用真实短信服务")
    sms_region_id: str = Field(default="cn-hangzhou", description="短信服务区域")
    sms_sign_name: str = Field(default="", description="短信签名名称")
    sms_template_code: str = Field(default="", description="短信模板CODE")

    # GitHub OAuth 配置
    github_client_id: str = Field(default="", description="GitHub OAuth Client ID")
    github_client_secret: str = Field(default="", description="GitHub OAuth Client Secret")
    github_redirect_uri: str = Field(default="http://localhost:8000/api/auth/github/callback", description="GitHub 回调地址")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level 必须是 {valid_levels} 之一")
        return v.upper()

    @field_validator("chroma_persist_dir", mode="before")
    @classmethod
    def validate_chroma_dir(cls, v) -> Path:
        """确保 ChromaDB 目录存在"""
        if isinstance(v, str):
            path = Path(v)
        else:
            path = v
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def mysql_url(self) -> Optional[str]:
        """生成 MySQL 连接 URL"""
        if self.mysql_host and self.mysql_user and self.mysql_database:
            password_part = f":{self.mysql_password}" if self.mysql_password else ""
            return (
                f"mysql+asyncmy://{self.mysql_user}{password_part}"
                f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            )
        return None

    @property
    def database_url(self) -> Optional[str]:
        """生成数据库连接 URL（优先 MySQL，备选 SQLite）"""
        if self.mysql_url:
            return self.mysql_url
        # 如果没有配置 MySQL，使用 SQLite 作为备选
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{data_dir / 'enterprise_doc_qa.db'}"

    model_config = SettingsModelConfig(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# 全局配置实例
settings = Settings()
