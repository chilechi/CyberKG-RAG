from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship

from app.core.config import Settings
from app.schemas.graph import GraphData, GraphEdge, GraphNode


def _node_to_schema(node: Node) -> GraphNode:
    """把 Neo4j 节点转换成前端图谱组件需要的稳定字段。"""
    return GraphNode(
        id=str(node.get("id", "")),
        name=str(node.get("name", "")),
        type=str(node.get("type", "")),
        description=str(node.get("description", "")),
    )


def _relationship_to_schema(relationship: Relationship) -> GraphEdge:
    """把 Neo4j 关系转换成 source/target/relation 边结构。"""
    return GraphEdge(
        source=str(relationship.start_node.get("id", "")),
        target=str(relationship.end_node.get("id", "")),
        relation=str(relationship.get("relation", relationship.type)),
    )


def get_neighbor_graph(settings: Settings, entity_id: str, depth: int) -> GraphData:
    """查询指定实体的邻居子图，并对节点和边去重。"""
    if depth < 1 or depth > 4:
        raise ValueError("depth must be between 1 and 4")

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    nodes: dict[str, GraphNode] = {}
    edges: dict[tuple[str, str, str], GraphEdge] = {}

    try:
        with driver.session() as session:
            result = session.run(
                f"""
                MATCH path = (start:Entity {{id: $entity_id}})-[*1..{depth}]-(neighbor:Entity)
                RETURN path
                """,
                entity_id=entity_id,
            )

            for record in result:
                path = record["path"]
                for node in path.nodes:
                    schema_node = _node_to_schema(node)
                    if schema_node.id:
                        nodes[schema_node.id] = schema_node
                for relationship in path.relationships:
                    schema_edge = _relationship_to_schema(relationship)
                    key = (schema_edge.source, schema_edge.target, schema_edge.relation)
                    edges[key] = schema_edge
    finally:
        driver.close()

    return GraphData(nodes=list(nodes.values()), edges=list(edges.values()))
