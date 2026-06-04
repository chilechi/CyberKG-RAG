import httpx

from app.core.config import Settings
from app.schemas.qa import QaEvidence


def _normalize_text(value: str) -> str:
    return value.lower().replace("-", " ").replace("_", " ")


def _keyword_overlap_score(query: str, text: str) -> float:
    """计算问题关键词在候选证据中的覆盖度，作为规则重排的可解释补充分。"""
    query_terms = {term for term in _normalize_text(query).split() if len(term) >= 2}
    if not query_terms:
        return 0.0

    normalized_text = _normalize_text(text)
    matched_terms = sum(1 for term in query_terms if term in normalized_text)
    return matched_terms / len(query_terms)


def _entity_match_score(query: str, evidence: QaEvidence) -> float:
    """检查问题中是否直接命中实体编号或来源名称。"""
    normalized_query = _normalize_text(query)
    entity_id = _normalize_text(evidence.entity_id)
    source = _normalize_text(evidence.source)

    score = 0.0
    if entity_id and entity_id in normalized_query:
        score += 0.7
    if source and source in normalized_query:
        score += 0.3
    return min(score, 1.0)


def _build_rule_reason(keyword_score: float, entity_score: float) -> str:
    reasons = ["向量相似度"]
    if keyword_score > 0:
        reasons.append("关键词命中")
    if entity_score > 0:
        reasons.append("实体/来源命中")
    return " + ".join(reasons)


def _rule_rerank(query: str, evidence: list[QaEvidence], top_k: int, *, fallback_reason: str = "") -> list[QaEvidence]:
    """无外部 rerank 服务时的规则重排兜底。"""
    scored_items: list[QaEvidence] = []
    for item in evidence:
        keyword_score = _keyword_overlap_score(query, item.text)
        entity_score = _entity_match_score(query, item)
        rerank_score = min(1.0, item.score * 0.6 + keyword_score * 0.25 + entity_score * 0.15)
        rank_reason = _build_rule_reason(keyword_score, entity_score)
        if fallback_reason:
            rank_reason = f"{rank_reason}；{fallback_reason}"
        scored_items.append(item.model_copy(update={"rerank_score": rerank_score, "rank_reason": rank_reason}))

    ranked = sorted(scored_items, key=lambda item: (item.rerank_score, item.score), reverse=True)
    return ranked[:top_k]


def _normalize_dashscope_score(score: float) -> float:
    """保留 DashScope 的绝对相关度语义，只做 0-1 边界裁剪。"""
    return max(0.0, min(1.0, score))


def _dashscope_rerank(settings: Settings, query: str, evidence: list[QaEvidence], top_k: int) -> list[QaEvidence]:
    """调用 DashScope 文本重排模型，对 Milvus 候选证据做语义相关性排序。"""
    response = httpx.post(
        settings.dashscope_rerank_url,
        headers={
            "Authorization": f"Bearer {settings.dashscope_rerank_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.rerank_model,
            "input": {
                "query": query,
                "documents": [item.text for item in evidence],
            },
            "parameters": {
                "top_n": min(top_k, len(evidence)),
                "return_documents": False,
            },
        },
        timeout=settings.rerank_timeout,
    )
    response.raise_for_status()
    payload = response.json()
    results = payload.get("output", {}).get("results", [])
    if not isinstance(results, list):
        raise ValueError(f"Unexpected DashScope rerank response: {payload}")

    ranked: list[QaEvidence] = []
    for result in results:
        index = int(result["index"])
        raw_score = float(result.get("relevance_score", result.get("score", 0.0)))
        rerank_score = _normalize_dashscope_score(raw_score)
        original = evidence[index]
        ranked.append(
            original.model_copy(
                update={
                    "rerank_score": rerank_score,
                    "rank_reason": f"DashScope {settings.rerank_model} 语义重排",
                }
            )
        )
    return ranked[:top_k]


def rerank_evidence(settings: Settings, query: str, evidence: list[QaEvidence], top_k: int) -> list[QaEvidence]:
    """优先使用配置的 rerank 服务；不可用时自动回退到规则重排。"""
    if not evidence:
        return []

    provider = settings.rerank_provider.lower()
    if provider == "dashscope" and settings.dashscope_rerank_api_key:
        try:
            return _dashscope_rerank(settings, query, evidence, top_k)
        except Exception as exc:  # noqa: BLE001 - rerank 失败时保留问答链路可用性
            return _rule_rerank(query, evidence, top_k, fallback_reason=f"DashScope rerank 失败，已回退：{exc.__class__.__name__}")

    return _rule_rerank(query, evidence, top_k)
