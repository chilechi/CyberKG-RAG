from pymilvus import connections, utility

from app.core.config import Settings


MILVUS_ALIAS = "healthcheck"


def check_milvus(settings: Settings) -> None:
    """连接 Milvus 并读取服务版本，确认向量数据库可用。"""
    connections.connect(
        alias=MILVUS_ALIAS,
        host=settings.milvus_host,
        port=str(settings.milvus_port),
    )
    try:
        utility.get_server_version(using=MILVUS_ALIAS)
    finally:
        connections.disconnect(MILVUS_ALIAS)
