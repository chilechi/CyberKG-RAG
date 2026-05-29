from neo4j import GraphDatabase
from neo4j.graph import Node, Relationship

from app.core.config import Settings
from app.schemas.graph import GraphData, GraphEdge, GraphNode

MAX_GRAPH_NODES = 45
MAX_GRAPH_EDGES = 70
MAX_QUERY_PATHS = 500

RELATION_PRIORITY = {
    "HAS_WEAKNESS": 1,
    "RELATED_TO_CAPEC": 2,
    "USES_TECHNIQUE": 3,
    "BELONGS_TO_TACTIC": 4,
    "HAS_MITIGATION": 5,
    "AFFECTS_PRODUCT": 6,
}


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


def _trim_graph(
    nodes: dict[str, GraphNode],
    edges: dict[tuple[str, str, str], GraphEdge],
    root_id: str,
) -> GraphData:
    """优先保留和查询实体相关的安全链路，避免图谱一次性展开过多。"""
    kept_node_ids: set[str] = {root_id} if root_id in nodes else set()
    kept_edges: list[GraphEdge] = []

    def edge_sort_key(edge: GraphEdge) -> tuple[int, int, str, str, str]:
        is_direct = edge.source == root_id or edge.target == root_id
        return (
            0 if is_direct else 1,
            RELATION_PRIORITY.get(edge.relation, 99),
            edge.source,
            edge.relation,
            edge.target,
        )

    for edge in sorted(edges.values(), key=edge_sort_key):
        next_node_ids = kept_node_ids | {edge.source, edge.target}
        if len(next_node_ids) > MAX_GRAPH_NODES:
            continue

        kept_edges.append(edge)
        kept_node_ids = next_node_ids

        if len(kept_edges) >= MAX_GRAPH_EDGES:
            break

    kept_nodes = [node for node_id, node in nodes.items() if node_id in kept_node_ids]
    return GraphData(nodes=kept_nodes, edges=kept_edges)


def get_neighbor_graph(settings: Settings, entity_id: str, depth: int) -> GraphData:
    """查询指定实体的邻居子图，并对节点和边去重。"""
    if depth < 1 or depth > 3:
        raise ValueError("depth must be between 1 and 3")

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
                LIMIT {MAX_QUERY_PATHS}
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

    return _trim_graph(nodes, edges, entity_id)
