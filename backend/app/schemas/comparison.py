from pydantic import BaseModel, Field

from app.schemas.qa import QaEvidence


class QaComparisonRequest(BaseModel):
    """问答对比实验请求。"""

    question: str = Field(..., min_length=1, description="用于对比三种问答模式的问题")


class QaComparisonResult(BaseModel):
    """单个问答模式的实验结果。"""

    mode: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    elapsed_ms: int
    graph_path_count: int
    text_evidence_count: int
    graph_paths: list[list[str]]
    text_evidence: list[QaEvidence]


class QaComparisonMetric(BaseModel):
    """对比实验的聚合指标。"""

    best_mode: str
    fastest_mode: str
    max_confidence: float
    total_elapsed_ms: int


class QaComparisonResponse(BaseModel):
    """问答对比实验响应。"""

    question: str
    results: list[QaComparisonResult]
    metrics: QaComparisonMetric


class QaEvaluationModeSummary(BaseModel):
    """离线问答评测中单个模式的平均指标。"""

    avg_final_score: float
    avg_entity_hit_rate: float
    avg_relation_hit_rate: float
    avg_keyword_coverage: float
    avg_evidence_score: float = 0.0
    avg_confidence: float = 0.0
    avg_graph_path_count: float = 0.0
    avg_text_evidence_count: float = 0.0
    avg_elapsed_ms: float
    case_count: int


class QaEvaluationResult(BaseModel):
    """离线问答评测中单个问题的详细结果。"""

    id: str
    question: str
    reference_answer: str
    expected_entities: list[str]
    expected_relations: list[str]
    expected_keywords: list[str]
    best_mode: str
    results: list[dict]


class QaEvaluationResponse(BaseModel):
    """从 experiments/qa_eval 读取的问答评测报告。"""

    case_count: int
    best_mode: str
    mode_summary: dict[str, QaEvaluationModeSummary]
    cases: list[QaEvaluationResult]
