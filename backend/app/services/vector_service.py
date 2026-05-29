from pymilvus import Collection, connections

from app.core.config import Settings
from app.schemas.qa import QaEvidence
from app.services.embedding_service import embed_text


def _normalize_text(value: str) -> str:
    return value.lower().replace("-", " ").replace("_", " ")


def _keyword_overlap_score(query: str, text: str) -> float:
    """用轻量关键词覆盖补充向量相似度，避免只按 embedding 分数排序。"""
    query_terms = {term for term in _normalize_text(query).split() if len(term) >= 2}
    if not query_terms:
        return 0.0

    normalized_text = _normalize_text(text)
    matched_terms = sum(1 for term in query_terms if term in normalized_text)
    return matched_terms / len(query_terms)


def _entity_match_score(query: str, evidence: QaEvidence) -> float:
    normalized_query = _normalize_text(query)
    entity_id = _normalize_text(evidence.entity_id)
    source = _normalize_text(evidence.source)

    score = 0.0
    if entity_id and entity_id in normalized_query:
        score += 0.7
    if source and source in normalized_query:
        score += 0.3
    return min(score, 1.0)


def _build_rank_reason(keyword_score: float, entity_score: float) -> str:
    reasons = ["向量相似度"]
    if keyword_score > 0:
        reasons.append("关键词命中")
    if entity_score > 0:
        reasons.append("实体/来源命中")
    return " + ".join(reasons)


def _calc_rerank_score(query: str, evidence: QaEvidence) -> tuple[float, str]:
    keyword_score = _keyword_overlap_score(query, evidence.text)
    entity_score = _entity_match_score(query, evidence)
    rerank_score = evidence.score * 0.6 + keyword_score * 0.25 + entity_score * 0.15
    return min(1.0, rerank_score), _build_rank_reason(keyword_score, entity_score)


def _rerank_evidence(query: str, evidence: list[QaEvidence], top_k: int) -> list[QaEvidence]:
    """按向量分、关键词命中和实体命中做二次排序，保留可解释的 Top-K 证据。"""
    scored_items: list[QaEvidence] = []
    for item in evidence:
        rerank_score, rank_reason = _calc_rerank_score(query, item)
        scored_items.append(item.model_copy(update={"rerank_score": rerank_score, "rank_reason": rank_reason}))

    ranked = sorted(
        scored_items,
        key=lambda item: (item.rerank_score, item.score),
        reverse=True,
    )
    return ranked[:top_k]


def search_doc_chunks(settings: Settings, query: str, top_k: int = 5) -> list[QaEvidence]:
    """从 Milvus 检索相似片段，并做轻量重排后返回 Top-K 文本证据。"""
    connections.connect(host=settings.milvus_host, port=str(settings.milvus_port))
    try:
        collection = Collection(settings.milvus_collection)
        collection.load()
        candidate_limit = min(max(top_k * 3, top_k), 30)
        results = collection.search(
            data=[embed_text(settings, query)],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=candidate_limit,
            output_fields=["entity_id", "entity_type", "source", "text"],
        )

        evidence: list[QaEvidence] = []
        for hit in results[0]:
            evidence.append(
                QaEvidence(
                    source=str(hit.entity.get("source")),
                    entity_id=str(hit.entity.get("entity_id")),
                    text=str(hit.entity.get("text")),
                    score=max(0.0, min(1.0, float(hit.score))),
                )
            )
        return _rerank_evidence(query, evidence, top_k)
    finally:
        connections.disconnect("default")
