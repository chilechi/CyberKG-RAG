from app.core.config import Settings
from app.schemas.qa import QaResponse
from app.services.graph_service import get_neighbor_graph
from app.services.vector_service import search_doc_chunks


DEFAULT_ENTITY_ID = "CVE-2021-44228"


def _pick_entity_id(question: str) -> str:
    """第一版用简单规则识别实体，后续替换为实体链接模块。"""
    normalized = question.upper()
    if "CVE-2021-44228" in normalized or "LOG4SHELL" in normalized:
        return "CVE-2021-44228"
    return DEFAULT_ENTITY_ID


def _build_paths(graph_edges) -> list[list[str]]:
    """把当前样例链式图谱边组织成路径展示格式。"""
    if not graph_edges:
        return []

    next_by_source = {edge.source: edge.target for edge in graph_edges}
    relation_by_pair = {(edge.source, edge.target): edge.relation for edge in graph_edges}
    targets = {edge.target for edge in graph_edges}
    starts = [edge.source for edge in graph_edges if edge.source not in targets]
    start = starts[0] if starts else graph_edges[0].source

    path = [start]
    current = start
    visited = {current}
    while current in next_by_source:
        target = next_by_source[current]
        relation = relation_by_pair.get((current, target), "")
        # 路径里保留关系名，便于前端和报告展示证据链。
        if relation:
            path.append(relation)
        path.append(target)
        if target in visited:
            break
        visited.add(target)
        current = target
    return [path]


def _build_answer(question: str, graph_paths: list[list[str]], evidence_count: int) -> str:
    if graph_paths:
        path_text = " -> ".join(graph_paths[0])
        return (
            f"针对问题“{question}”，系统从安全知识图谱中检索到证据路径：{path_text}。"
            f"同时从向量库召回 {evidence_count} 条相关文本证据。"
            "当前答案由规则模板生成，后续可接入 DeepSeek API 基于这些证据生成更自然的分析结论。"
        )
    return (
        f"针对问题“{question}”，当前图谱中没有检索到明确路径。"
        f"系统仍从向量库召回 {evidence_count} 条文本证据，建议人工核查后再生成结论。"
    )


def answer_with_kg_rag(settings: Settings, question: str) -> QaResponse:
    """组合 Neo4j 图谱路径和 Milvus 文本证据，形成第一版 KG-RAG 闭环。"""
    entity_id = _pick_entity_id(question)
    graph = get_neighbor_graph(settings, entity_id=entity_id, depth=4)
    text_evidence = search_doc_chunks(settings, query=question, top_k=3)
    graph_paths = _build_paths(graph.edges)
    confidence = 0.4
    if graph_paths:
        confidence += 0.3
    if text_evidence:
        confidence += min(0.3, len(text_evidence) * 0.1)

    return QaResponse(
        question=question,
        answer=_build_answer(question, graph_paths, len(text_evidence)),
        graph_paths=graph_paths,
        text_evidence=text_evidence,
        confidence=min(confidence, 0.95),
    )
