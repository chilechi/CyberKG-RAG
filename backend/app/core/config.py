from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """应用配置，从项目根目录 .env 读取数据库和外部服务参数。"""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "cyberkg"
    postgres_user: str = "cyberkg"
    postgres_password: str = "cyberkg"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_collection: str = "cyber_doc_chunks"

    embedding_provider: str = "mock"
    embedding_model: str = "text-embedding-v4"
    embedding_dim: int = 1024
    dashscope_api_key: str = ""
    dashscope_embedding_url: str = (
        "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout: int = 60

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def postgres_url(self) -> str:
        """SQLAlchemy 使用的 PostgreSQL 连接串。"""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求重复解析 .env。"""
    return Settings()
