from app.schemas.qa import QaEvidence


def _average_rerank_score(text_evidence: list[QaEvidence]) -> float:
    if not text_evidence:
        return 0.0
    return sum(item.rerank_score for item in text_evidence) / len(text_evidence)


def calculate_llm_confidence(has_model_answer: bool) -> float:
    """普通 LLM 没有外部证据，只根据是否拿到真实模型回复给基础可信度。"""
    return 0.55 if has_model_answer else 0.15


def calculate_rag_confidence(text_evidence: list[QaEvidence], has_model_answer: bool) -> float:
    """普通 RAG 主要看文本证据质量，辅以模型是否成功生成。"""
    avg_rerank = _average_rerank_score(text_evidence)
    evidence_count_score = min(len(text_evidence) / 5, 1.0)
    model_score = 0.1 if has_model_answer else 0.0
    confidence = 0.2 + avg_rerank * 0.45 + evidence_count_score * 0.1 + model_score
    return min(confidence, 0.8)


def calculate_kg_rag_confidence(
    *,
    entity_matched: bool,
    graph_path_count: int,
    text_evidence: list[QaEvidence],
    has_model_answer: bool,
) -> float:
    """KG-RAG 同时考虑实体识别、图谱路径、文本证据质量和模型生成状态。"""
    avg_rerank = _average_rerank_score(text_evidence)
    graph_score = min(graph_path_count / 8, 1.0)
    evidence_count_score = min(len(text_evidence) / 5, 1.0)
    confidence = 0.2
    confidence += 0.15 if entity_matched else 0.0
    confidence += graph_score * 0.25
    confidence += avg_rerank * 0.3
    confidence += evidence_count_score * 0.05
    confidence += 0.05 if has_model_answer else 0.0
    return min(confidence, 0.95)
