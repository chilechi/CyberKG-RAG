from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.core.config import Settings


def create_postgres_engine(settings: Settings) -> Engine:
    """创建 PostgreSQL engine，后续业务模块复用这个连接入口。"""
    return create_engine(settings.postgres_url, pool_pre_ping=True)


def check_postgres(settings: Settings) -> None:
    """执行最小 SQL，确认 PostgreSQL 可连接且认证可用。"""
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    finally:
        engine.dispose()
