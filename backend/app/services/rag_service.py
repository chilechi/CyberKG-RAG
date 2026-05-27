from app.core.config import Settings
from app.schemas.qa import QaResponse
from app.services.entity_service import identify_entity
from app.services.graph_service import get_neighbor_graph
from app.services.vector_service import search_doc_chunks


DEFAULT_ENTITY_ID = "CVE-2021-44228"


def _build_paths(graph_edges) -> list[list[str]]:
    """把图谱边转换成前端可展示的证据路径。"""
    paths = [
        [edge.source, edge.relation, edge.target]
        for edge in graph_edges
        if edge.source and edge.target and edge.relation
    ]
    return paths[:12]


def _pick_entity_id(settings: Settings, question: str, text_evidence) -> str:
    """优先用 PostgreSQL 实体识别，失败时用 Milvus 召回的首条证据兜底。"""
    matched_entity = identify_entity(settings, question)
    if matched_entity:
        return matched_entity.id
    if text_evidence:
        return text_evidence[0].entity_id
    return DEFAULT_ENTITY_ID


def _build_answer(question: str, entity_id: str, graph_paths: list[list[str]], evidence_count: int) -> str:
    if not graph_paths and evidence_count == 0:
        return (
            f"针对问题“{question}”，当前知识库没有检索到足够的图谱路径或文本证据。"
            "为了避免无依据生成，系统暂时无法给出可靠结论。"
        )

    path_text = "；".join(" -> ".join(path) for path in graph_paths[:5]) if graph_paths else "暂无图谱路径"
    return (
        f"针对问题“{question}”，系统识别到核心实体 {entity_id}。"
        f"图谱检索得到 {len(graph_paths)} 条证据边，文本检索召回 {evidence_count} 条相关片段。"
        f"主要图谱证据包括：{path_text}。"
        "当前答案仍由规则模板生成，下一步会接入 DeepSeek 基于这些证据生成更自然的攻击原理、影响范围和防护建议。"
    )


def answer_with_kg_rag(settings: Settings, question: str) -> QaResponse:
    """组合实体识别、Neo4j 图谱路径和 Milvus 文本证据，形成 KG-RAG 闭环。"""
    text_evidence = search_doc_chunks(settings, query=question, top_k=5)
    entity_id = _pick_entity_id(settings, question, text_evidence)
    graph = get_neighbor_graph(settings, entity_id=entity_id, depth=2)
    graph_paths = _build_paths(graph.edges)

    confidence = 0.25
    if entity_id != DEFAULT_ENTITY_ID or DEFAULT_ENTITY_ID.upper() in question.upper():
        confidence += 0.2
    if graph_paths:
        confidence += min(0.3, len(graph_paths) * 0.04)
    if text_evidence:
        confidence += min(0.25, len(text_evidence) * 0.05)

    return QaResponse(
        question=question,
        answer=_build_answer(question, entity_id, graph_paths, len(text_evidence)),
        graph_paths=graph_paths,
        text_evidence=text_evidence,
        confidence=min(confidence, 0.95),
    )
