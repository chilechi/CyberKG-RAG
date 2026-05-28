from pymilvus import Collection, connections
from sqlalchemy import text

from app.core.config import Settings
from app.db.postgres import create_postgres_engine
from app.schemas.data_management import DataImportStep, DataManagementSummary, DataMetric, DataSourceItem


def _count_postgres(settings: Settings, table_name: str) -> int:
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            return int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    finally:
        engine.dispose()


def _count_milvus(settings: Settings) -> int:
    connections.connect(alias="data_management", host=settings.milvus_host, port=settings.milvus_port)
    try:
        collection = Collection(settings.milvus_collection, using="data_management")
        collection.load()
        return int(collection.num_entities)
    finally:
        connections.disconnect(alias="data_management")


def _load_sources(settings: Settings) -> list[DataSourceItem]:
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT source, COUNT(*) AS document_count
                    FROM doc_chunks
                    GROUP BY source
                    ORDER BY document_count DESC, source ASC
                    """
                )
            )
            return [
                DataSourceItem(
                    name=str(row.source),
                    source_type="文档片段",
                    storage_targets=["PostgreSQL", "Milvus"],
                    document_count=int(row.document_count),
                )
                for row in rows
            ]
    finally:
        engine.dispose()


def _safe_count(counter) -> int | None:
    try:
        return counter()
    except Exception:  # noqa: BLE001 - 数据页需要在部分依赖失败时继续展示其它数据
        return None


def build_data_management_summary(settings: Settings) -> DataManagementSummary:
    entity_count = _safe_count(lambda: _count_postgres(settings, "entities"))
    relation_count = _safe_count(lambda: _count_postgres(settings, "relations"))
    document_count = _safe_count(lambda: _count_postgres(settings, "doc_chunks"))
    vector_count = _safe_count(lambda: _count_milvus(settings))
    sources = _load_sources(settings) if document_count is not None else []

    metrics = [
        DataMetric(key="sources", label="数据源数量", value=len(sources), description="按 doc_chunks.source 聚合"),
        DataMetric(key="documents", label="文档片段", value=document_count, description="PostgreSQL doc_chunks"),
        DataMetric(key="vectors", label="向量数量", value=vector_count, description="Milvus collection"),
        DataMetric(key="entities", label="图谱实体", value=entity_count, description="PostgreSQL entities"),
        DataMetric(key="relations", label="图谱关系", value=relation_count, description="PostgreSQL relations"),
    ]

    import_steps = [
        DataImportStep(key="upload", label="读取样例数据", description="data/samples JSON 文件", count=document_count),
        DataImportStep(key="postgres", label="写入 PostgreSQL", description="实体、关系、文档片段", count=(entity_count or 0) + (relation_count or 0) + (document_count or 0) if None not in [entity_count, relation_count, document_count] else None),
        DataImportStep(key="milvus", label="文本向量入库", description="文档片段 embedding", count=vector_count),
        DataImportStep(key="neo4j", label="图谱关系入库", description="Neo4j 实体与关系", count=(entity_count or 0) + (relation_count or 0) if None not in [entity_count, relation_count] else None),
    ]

    return DataManagementSummary(metrics=metrics, sources=sources, import_steps=import_steps)
