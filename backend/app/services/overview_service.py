from collections.abc import Callable

from neo4j import GraphDatabase
from pymilvus import Collection, connections
from sqlalchemy import text

from app.core.config import Settings
from app.db.postgres import create_postgres_engine
from app.schemas.overview import DependencyStatus, DistributionItem, FlowStep, MetricCard, OverviewSummary


def _safe_count(label: str, counter: Callable[[], int]) -> tuple[int | None, DependencyStatus]:
    """单个数据源失败时不拖垮总览页，只把对应状态标为异常。"""
    try:
        value = counter()
        return value, DependencyStatus(name=label, status="ok", message="连接正常")
    except Exception as exc:  # noqa: BLE001 - 总览页需要兜底展示各依赖状态
        return None, DependencyStatus(name=label, status="error", message=str(exc))


def _safe_distribution(label: str, loader: Callable[[], list[DistributionItem]]) -> tuple[list[DistributionItem], DependencyStatus]:
    """分布数据读取失败时返回空列表，页面展示暂无数据。"""
    try:
        return loader(), DependencyStatus(name=label, status="ok", message="聚合成功")
    except Exception as exc:  # noqa: BLE001 - 聚合接口需要把错误降级为状态
        return [], DependencyStatus(name=label, status="error", message=str(exc))


def _count_postgres(settings: Settings, table_name: str) -> int:
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            return int(connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())
    finally:
        engine.dispose()


def _postgres_distribution(settings: Settings, table_name: str, column_name: str) -> list[DistributionItem]:
    engine = create_postgres_engine(settings)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""
                    SELECT {column_name} AS label, COUNT(*) AS count
                    FROM {table_name}
                    GROUP BY {column_name}
                    ORDER BY count DESC, label ASC
                    """
                )
            )
            return [
                DistributionItem(key=str(row.label), label=str(row.label), count=int(row.count))
                for row in rows
                if row.label is not None
            ]
    finally:
        engine.dispose()


def _count_neo4j(settings: Settings, cypher: str) -> int:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        with driver.session() as session:
            return int(session.run(cypher).single()["count"])
    finally:
        driver.close()


def _count_milvus(settings: Settings) -> int:
    connections.connect(
        alias="overview",
        host=settings.milvus_host,
        port=settings.milvus_port,
    )
    try:
        collection = Collection(settings.milvus_collection, using="overview")
        collection.load()
        return int(collection.num_entities)
    finally:
        connections.disconnect(alias="overview")


def _status_from_count(value: int | None) -> str:
    if value is None:
        return "error"
    if value == 0:
        return "empty"
    return "ready"


def build_overview_summary(settings: Settings) -> OverviewSummary:
    entity_count, pg_entities_status = _safe_count(
        "PostgreSQL 实体表",
        lambda: _count_postgres(settings, "entities"),
    )
    relation_count, pg_relations_status = _safe_count(
        "PostgreSQL 关系表",
        lambda: _count_postgres(settings, "relations"),
    )
    doc_count, pg_docs_status = _safe_count(
        "PostgreSQL 文档片段表",
        lambda: _count_postgres(settings, "doc_chunks"),
    )
    graph_node_count, neo4j_nodes_status = _safe_count(
        "Neo4j 节点",
        lambda: _count_neo4j(settings, "MATCH (n:Entity) RETURN count(n) AS count"),
    )
    graph_relation_count, neo4j_relations_status = _safe_count(
        "Neo4j 关系",
        lambda: _count_neo4j(settings, "MATCH ()-[r]->() RETURN count(r) AS count"),
    )
    vector_count, milvus_status = _safe_count(
        "Milvus 向量集合",
        lambda: _count_milvus(settings),
    )

    entity_types, entity_type_status = _safe_distribution(
        "实体类型分布",
        lambda: _postgres_distribution(settings, "entities", "type"),
    )
    relation_types, relation_type_status = _safe_distribution(
        "关系类型分布",
        lambda: _postgres_distribution(settings, "relations", "relation"),
    )
    document_sources, doc_source_status = _safe_distribution(
        "文档来源分布",
        lambda: _postgres_distribution(settings, "doc_chunks", "source"),
    )

    metrics = [
        MetricCard(key="entities", label="实体总数", value=entity_count, description="来自 PostgreSQL entities"),
        MetricCard(key="relations", label="关系总数", value=relation_count, description="来自 PostgreSQL relations"),
        MetricCard(key="documents", label="文档片段", value=doc_count, description="来自 PostgreSQL doc_chunks"),
        MetricCard(key="graph_nodes", label="图谱节点", value=graph_node_count, description="来自 Neo4j"),
        MetricCard(key="graph_relations", label="图谱关系", value=graph_relation_count, description="来自 Neo4j"),
        MetricCard(key="vectors", label="向量数量", value=vector_count, description="来自 Milvus"),
        MetricCard(key="qa_history", label="问答记录", value=None, status="reserved", description="历史记录表尚未实现"),
    ]

    flow_steps = [
        FlowStep(
            key="source",
            label="安全知识数据",
            description="实体、关系和文档片段样例数据",
            count=(entity_count or 0) + (relation_count or 0) + (doc_count or 0) if None not in [entity_count, relation_count, doc_count] else None,
            status=_status_from_count(doc_count),
        ),
        FlowStep(
            key="storage",
            label="三库入库",
            description="PostgreSQL、Neo4j、Milvus 数据已分层存储",
            count=(graph_node_count or 0) + (graph_relation_count or 0) + (vector_count or 0)
            if None not in [graph_node_count, graph_relation_count, vector_count]
            else None,
            status="ready" if all(item.status == "ok" for item in [pg_entities_status, neo4j_nodes_status, milvus_status]) else "error",
        ),
        FlowStep(
            key="retrieval",
            label="KG-RAG 检索",
            description="图谱路径和文本向量证据联合召回",
            count=vector_count,
            status=_status_from_count(vector_count),
        ),
        FlowStep(
            key="answer",
            label="可溯源答案",
            description="返回答案、图谱路径和文本证据",
            count=None,
            status="reserved",
        ),
    ]

    dependencies = [
        pg_entities_status,
        pg_relations_status,
        pg_docs_status,
        neo4j_nodes_status,
        neo4j_relations_status,
        milvus_status,
        entity_type_status,
        relation_type_status,
        doc_source_status,
    ]
    return OverviewSummary(
        metrics=metrics,
        dependencies=dependencies,
        entity_types=entity_types,
        relation_types=relation_types,
        document_sources=document_sources,
        flow_steps=flow_steps,
    )
