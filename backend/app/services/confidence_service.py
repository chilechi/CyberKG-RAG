from itertools import zip_longest

from app.schemas.qa import QaEvidence


def _weighted_top_rerank_score(text_evidence: list[QaEvidence]) -> float:
    """优先采用前 3 条证据的加权相关度，避免低分候选拖低强证据。"""
    if not text_evidence:
        return 0.0

    weights = [0.55, 0.25, 0.20]
    ranked = sorted(text_evidence, key=lambda item: item.rerank_score, reverse=True)[: len(weights)]
    total = 0.0
    total_weight = 0.0
    for item, weight in zip_longest(ranked, weights, fillvalue=None):
        if item is None or weight is None:
            continue
        total += item.rerank_score * weight
        total_weight += weight
    return total / (total_weight or 1.0)


def calculate_llm_confidence(has_model_answer: bool) -> float:
    """普通 LLM 没有外部证据，只根据是否拿到真实模型回答给基础可信度。"""
    return 0.55 if has_model_answer else 0.15


def calculate_rag_confidence(text_evidence: list[QaEvidence], has_model_answer: bool) -> float:
    """普通 RAG 主要依据 Top3 文本证据质量，而不是简单平均所有候选。"""
    weighted_rerank = _weighted_top_rerank_score(text_evidence)
    evidence_count_score = min(len(text_evidence) / 5, 1.0)
    model_score = 0.1 if has_model_answer else 0.0
    confidence = 0.18 + weighted_rerank * 0.52 + evidence_count_score * 0.1 + model_score
    return min(confidence, 0.85)


def calculate_kg_rag_confidence(
    *,
    entity_matched: bool,
    graph_path_count: int,
    text_evidence: list[QaEvidence],
    has_model_answer: bool,
) -> float:
    """KG-RAG 综合实体命中、图谱路径、Top3 文本证据质量和模型生成状态。"""
    weighted_rerank = _weighted_top_rerank_score(text_evidence)
    graph_score = min(graph_path_count / 8, 1.0)
    evidence_count_score = min(len(text_evidence) / 5, 1.0)
    confidence = 0.2
    confidence += 0.15 if entity_matched else 0.0
    confidence += graph_score * 0.25
    confidence += weighted_rerank * 0.3
    confidence += evidence_count_score * 0.05
    confidence += 0.05 if has_model_answer else 0.0
    return min(confidence, 0.95)
