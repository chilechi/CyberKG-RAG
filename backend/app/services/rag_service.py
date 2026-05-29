from app.core.config import Settings
from app.schemas.qa import QaResponse
from app.services.confidence_service import calculate_kg_rag_confidence
from app.services.entity_service import identify_entity
from app.services.graph_service import get_neighbor_graph
from app.services.llm_service import build_kg_rag_prompt, generate_with_deepseek
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
    try:
        matched_entity = identify_entity(settings, question)
    except Exception:  # noqa: BLE001 - PostgreSQL 临时不可用时允许问答链路继续降级
        matched_entity = None
    if matched_entity:
        return matched_entity.id
    if text_evidence:
        return text_evidence[0].entity_id
    return DEFAULT_ENTITY_ID


def _build_fallback_answer(question: str, entity_id: str, graph_paths: list[list[str]], evidence_count: int) -> str:
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
        "DeepSeek 当前未配置或调用失败，因此先返回基于证据的规则化答案。"
    )


def answer_with_kg_rag(settings: Settings, question: str) -> QaResponse:
    """组合实体识别、Neo4j 图谱路径和 Milvus 文本证据，形成 KG-RAG 闭环。"""
    try:
        text_evidence = search_doc_chunks(settings, query=question, top_k=5)
    except Exception:  # noqa: BLE001 - Milvus 不可用时保留问答接口可用性
        text_evidence = []
    entity_id = _pick_entity_id(settings, question, text_evidence)
    entity_matched = entity_id != DEFAULT_ENTITY_ID or DEFAULT_ENTITY_ID.upper() in question.upper()
    try:
        graph = get_neighbor_graph(settings, entity_id=entity_id, depth=2)
        graph_paths = _build_paths(graph.edges)
    except Exception:  # noqa: BLE001 - Neo4j 不可用时仍可基于文本证据或兜底提示返回
        graph_paths = []
    model_answer = generate_with_deepseek(
        settings,
        build_kg_rag_prompt(question, entity_id, graph_paths, text_evidence),
    )
    answer = model_answer or _build_fallback_answer(question, entity_id, graph_paths, len(text_evidence))

    return QaResponse(
        question=question,
        mode="KG-RAG",
        answer=answer,
        graph_paths=graph_paths,
        text_evidence=text_evidence,
        confidence=calculate_kg_rag_confidence(
            entity_matched=entity_matched,
            graph_path_count=len(graph_paths),
            text_evidence=text_evidence,
            has_model_answer=model_answer is not None,
        ),
    )
